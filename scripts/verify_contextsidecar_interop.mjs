import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';

const proofgridRoot = resolve(import.meta.dirname, '..');
const contextRoot = process.env.CONTEXT_SIDECAR_ROOT;
const python = process.env.PROOFGRID_PYTHON;
if (!contextRoot || !python) {
  throw new Error('Set CONTEXT_SIDECAR_ROOT and PROOFGRID_PYTHON to run the interop proof.');
}

function run(command, args, options = {}) {
  return new Promise((resolveRun, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd ?? proofgridRoot,
      env: options.env ?? process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => (stdout += chunk.toString()));
    child.stderr.on('data', (chunk) => (stderr += chunk.toString()));
    child.on('error', reject);
    child.on('exit', (code) => {
      if (code === 0) resolveRun({ stdout, stderr });
      else reject(new Error(`${command} exited ${code}\n${stdout}\n${stderr}`));
    });
  });
}

const temp = mkdtempSync(resolve(tmpdir(), 'proofgrid-contextsidecar-interop-'));
const key = 'interop-secret-that-must-not-persist';
let calls = 0;
const server = createServer((request, response) => {
  const chunks = [];
  request.on('data', (chunk) => chunks.push(chunk));
  request.on('end', () => {
    calls += 1;
    const body = Buffer.concat(chunks).toString('utf8');
    if (request.headers.authorization !== `Bearer ${key}`) {
      response.writeHead(401).end();
      return;
    }
    const waitMs = body.includes('slow-model') ? 18 : 4;
    response.writeHead(200, { 'Content-Type': 'text/event-stream' });
    response.write(`data: ${JSON.stringify({ choices: [{ delta: { content: 'Grounded ' } }] })}\n\n`);
    setTimeout(() => {
      response.write(
        `data: ${JSON.stringify({
          choices: [{ delta: { content: 'answer.' } }],
          usage: { prompt_tokens: 100, completion_tokens: 10, total_tokens: 110 },
        })}\n\n`,
      );
      response.end('data: [DONE]\n\n');
    }, waitMs);
  });
});

await new Promise((ready) => server.listen(0, '127.0.0.1', ready));
const address = server.address();
if (!address || typeof address === 'string') throw new Error('Interop server did not bind.');

try {
  const bundles = [];
  for (const candidate of [
    { id: 'fast-path', model: 'fast-model' },
    { id: 'slow-path', model: 'slow-model' },
  ]) {
    const output = resolve(temp, `${candidate.id}.json`);
    await run(
      process.execPath,
      [resolve(contextRoot, 'node_modules/vite-node/dist/cli.mjs'), '--script', 'tools/answer-observation-capture.ts'],
      {
        cwd: contextRoot,
        env: {
          ...process.env,
          ANSWER_API_KEY: key,
          ANSWER_CANDIDATE_ID: candidate.id,
          ANSWER_PROVIDER: 'local-interop',
          ANSWER_BASE_URL: `http://127.0.0.1:${address.port}/v1`,
          ANSWER_MODEL: candidate.model,
          ANSWER_OBSERVATIONS_OUTPUT: output,
          ANSWER_DELAY_MS: '0',
          ANSWER_TIMEOUT_MS: '5000',
        },
      },
    );
    bundles.push(output);
  }
  await new Promise((done) => server.close(done));

  const pricingPath = resolve(temp, 'pricing.json');
  writeFileSync(
    pricingPath,
    `${JSON.stringify(
      {
        'fast-path': { input_per_million_usd: 1, output_per_million_usd: 2, source: 'interop-fixture' },
        'slow-path': { input_per_million_usd: 2, output_per_million_usd: 4, source: 'interop-fixture' },
      },
      null,
      2,
    )}\n`,
  );
  const database = resolve(temp, 'runs.sqlite3');
  const imported = resolve(temp, 'imported.json');
  const importResult = await run(python, [
    '-m',
    'proofgrid.cli',
    'import-observations',
    '--bundle',
    bundles[0],
    '--bundle',
    bundles[1],
    '--pricing',
    pricingPath,
    '--db',
    database,
    '--output',
    imported,
  ]);
  const runId = JSON.parse(importResult.stdout).run_id;
  const reviewResult = await run(python, [
    '-m',
    'proofgrid.cli',
    'reviews',
    '--db',
    database,
    '--run-id',
    runId,
    '--status',
    'open',
  ]);
  const reviews = JSON.parse(reviewResult.stdout);
  if (reviews.length !== 30) throw new Error(`Expected 30 reviews, received ${reviews.length}.`);
  const reviewPath = resolve(temp, 'review.json');
  writeFileSync(
    reviewPath,
    `${JSON.stringify(
      {
        reviewer: 'interop-reviewer',
        first_useful_delta_index: 1,
        scores: {
          addresses_question: 2,
          uses_approved_context: 2,
          no_unsupported_claim: 2,
          concise_for_realtime: 2,
          usable_structure: 2,
          clarifies_when_needed: 2,
        },
        note: 'The second observed delta completes the useful answer.',
      },
      null,
      2,
    )}\n`,
  );
  for (const review of reviews) {
    await run(python, [
      '-m',
      'proofgrid.cli',
      'review-answer',
      '--db',
      database,
      '--review-id',
      review.review_id,
      '--review',
      reviewPath,
    ]);
  }
  const finalPath = resolve(temp, 'final.json');
  await run(python, [
    '-m',
    'proofgrid.cli',
    'export',
    '--db',
    database,
    '--format',
    'json',
    '--output',
    finalPath,
  ]);
  const final = JSON.parse(readFileSync(finalPath, 'utf8'));
  const serialized = JSON.stringify(final);
  if (final.decision.winner !== 'fast-path') throw new Error('Expected the faster, cheaper passing path to win.');
  if (!final.candidates.every((candidate) => candidate.summary.promoted)) {
    throw new Error('Both reviewed candidates should pass the frozen interop fixture.');
  }
  if (serialized.includes(key)) throw new Error('ProofGrid result persisted the provider key.');
  console.log(
    `CONTEXTSIDECAR_PROOFGRID_INTEROP_PASS calls=${calls} observations=30 reviews=30 winner=${final.decision.winner}`,
  );
} finally {
  if (server.listening) await new Promise((done) => server.close(done));
  rmSync(temp, { recursive: true, force: true });
}
