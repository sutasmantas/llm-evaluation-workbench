# ProofGrid execution checkpoint

Last updated: 2026-08-06

## Decision

The ranked depth slice and the bounded ContextSidecar observation extension are
complete at minimum referenceable functionality. ProofGrid now evaluates
streamed outputs captured through an application's real adapter without
duplicating that adapter or moving generic evaluation logic into the app. Stop
before visual polish, additional providers, auth, hosting, or production
hardening.

## Restart boundary

- repository: `portfolio_demos/proofgrid`
- assigned worktree: `portfolio_demos/proofgrid`
- integrated branch: local `main`
- completed implementation branch: `agent/proofgrid-contextsidecar`
- upstream baseline: `b0e1055892bea1305a10f8d42fdc47ff1b41ffa4`
- foundation/identity commit: `98cdca8669e434e9bc234c2759a2cf71dff1f66b`
- application commit: `8d676c6a54df35af101447f5632163cc20e68a52`
- checkpoint/claim evidence commit: `54b6870ef6eb80028192f373d2bb2ff38125dd98`
- merge commit: `5535a4ae628b2ba170c32b53ed49487517e91be0`
- observation application commit: `4c40c43c19b8440a73f327674e01503ec1f68ae5`
- observation checkpoint commit: `34109bea8a736df56f3b7f9c5dc9ee4f913cadae`
- observation merge commit: `850156b0685485b474fc98dcc611106971a87035`
- observation closure commit: the commit containing this update
- expected restart state: clean local `main`, with the observation extension
  integrated and no portfolio remote or push
- remote: upstream AutoEvals only; no user portfolio remote, push, or deployment
- read-only exclusions: all other portfolio worktrees, especially ContextSidecar

## Exit gate

| Requirement | Status | Evidence |
| --- | --- | --- |
| GitHub foundation and pinned central reuse | PASS | `docs/PROJECT_START.md`, `THIRD_PARTY_REUSE.md`, preserved upstream commit/history |
| Distinct rendered identity before implementation | PASS | foundation commit plus identity and functional screenshots at 1440/1024/390 |
| CSV/JSONL import and bounded invalid-input behavior | PASS | parser/API plus duplicate, missing-heldout, malformed-JSON, size/count/format controls |
| Versioned prompt/model/provider runs | PASS | suite/schema/promotion/prompt/config hashes in every result |
| JSON Schema and structured-output validation | PASS | reused AutoEvals `ValidJSON` and frozen schema |
| Deterministic checks plus optional model judge | PASS | AutoEvals `JSONDiff`/`ExactMatch`; opt-in `--judge` and API flag with explicit credential gate |
| Quality/latency/token/cost/retry/rate-limit records | PASS | per-case JSON/CSV evidence; null-not-zero token contract; no-key USD 0 |
| Correction/review queue and regression gate | PASS | SQLite reviews, evidence-backed resolution, gate recomputation, browser flow |
| Deterministic no-key and OpenAI-compatible adapters | PASS | default run plus local-stub transient/permanent/usage tests |
| CLI/API output for client report or CI gate | PASS | `--require-winner`, JSON output, CSV export, REST endpoints |
| Frozen first experiment and decision rule | PASS | `evals/proofgrid`, committed experiment JSON/CSV |
| Expertise note and claim ledger | PASS | `docs/EXPERTISE_NOTES.md`, `docs/CLAIM_LEDGER.md` |
| Clean-checkout reproduction | PASS | detached `proofgrid_verify` at `54b6870`; locked `uv sync --extra dev`, formatting/static checks, 19 tests, and `proofgrid run --require-winner` all passed |

Every exit row is `PASS`; the slice is closed at minimum referenceable
functionality. The final closure commit is the commit containing this update
and is reported in the cross-portfolio checkpoint and handback.

## ContextSidecar observation extension gate

| Requirement | Status | Evidence |
| --- | --- | --- |
| Preserve the real application provider path | PASS | ContextSidecar exporter invokes its production TypeScript streamed adapter; ProofGrid imports the resulting versioned bundle |
| Reuse instead of cloning generic evaluation | PASS | AutoEvals `Score`, existing ProofGrid SQLite review store, reports, summaries, and decision layer |
| Reject non-comparable or unsafe evidence | PASS | same corpus/replay/context hashes and exact case contracts; ordered streams; privacy flags; credential-free endpoint; size/count controls |
| Review answer usefulness against observed evidence | PASS | six-dimension rubric and reviewer-selected real stream delta; no typed first-useful timestamp accepted |
| Compare candidates without unsupported provider claims | PASS | at least two frozen-input candidates; sourced cost, first-useful p95, completion p95 tie-break; provider-superiority claim disabled |
| CLI/API/CSV integration | PASS | import, review listing/resolution, persistence, recomputation, and answer evidence export |
| Cross-repository executable proof | PASS | 30 production-adapter mock calls, 30 imported observations, 30 persisted/resolved reviews, faster/cheaper passing fixture selected, key absent |
| Focused quality gate | PASS | Black, isort, Flake8, `git diff --check`, package build/Twine, and 23 focused/reused-foundation tests |

Every extension row is `PASS`. Real-provider quality remains a separate
credentialed experiment and is not implied by this gate.

## Shared-verification extension gate

| Requirement | Status | Evidence |
| --- | --- | --- |
| Audited executable-evaluation trigger | PASS | prior audit's conditional Inspect seam activated by FirstRing's executable agent workload |
| Immutable external execution engine | PASS | Inspect AI `cb00efcd12dfbf3e44f486648e05e54f1337fe9a`; observed version `0.3.253.dev7+gcb00efcd1`; locked optional environment |
| Narrow provider ownership | PASS | `proofgrid.inspect_integration` owns only JSON-Schema scoring and strict log normalization; Inspect retains execution/log ownership |
| Provider reference | PASS | raw log plus normalized 1/1 result under `docs/evidence/inspect-reference/` |
| Real independent consumer | PASS | FirstRing executes four application scenarios using a vendored ProofGrid wheel and consumer-local schemas |
| Relevant failure path | PASS | FirstRing provider failure, recovery, handoff exhaustion, and dead-letter final state satisfy the frozen oracle |
| Mutation evidence | PASS | fail-open unknown-FAQ mutation yields 3/4, `contract_mismatch`, no winner, and expected CLI exit 2 |
| Existing provider gate | PASS | Black, isort, Flake8, compileall, package/Twine, and 30 ProofGrid tests including seven real Inspect integration tests |

The extension is locally complete. It proves transfer of one executable
evaluation boundary and no broader model, agent, or provider-quality claim.

## Measured first experiment

Promotion was registered before the run: heldout schema pass = 1.0, exact pass
at least 0.95, mean task score at least 0.95, no open review, and no provider
failure. Tie-break: cost, retries, latency, stable candidate ID.

| Candidate | Heldout schema | Heldout exact | Mean task | Open reviews | Retry/rate limit | Promoted |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | 0.000000 | 0.000000 | 0.639384 | 6 | 0/0 | no |
| structured | 1.000000 | 0.833333 | 0.972222 | 1 | 0/0 | no |
| repair | 1.000000 | 1.000000 | 1.000000 | 0 | 1/1 simulated | yes |

The result promotes a path on these deterministic fixtures. It does not rank
providers or establish real-model quality.

## Verification evidence

- focused plus reused foundation: 19 passed; one upstream Starlette TestClient
  deprecation warning;
- formatting/static: Black check, isort check, Flake8, compileall, and
  `git diff --check` pass;
- package: sdist and wheel build; Twine check passes. The source checkout—not
  the wheel—is the verified UI/fixture quickstart;
- CLI: `proofgrid run --require-winner` exits 0 and promotes `repair`; JSON and
  55-line CSV artifacts committed;
- live API: health `ready`; real POST run, review query/correction, run reload,
  and CSV response pass;
- browser: 18 heldout matrix cells and PASS gate at 1440/1024/390; zero console
  errors; no body overflow; matrix-only horizontal scrolling at 390; correction
  changes the tie-break winner from repair to structured and disables repeat
  resolution.
- detached clean checkout: `54b6870`; `uv sync --extra dev` resolved and
  installed the lockfile, Black/isort/Flake8 passed, 19 tests passed, and the
  CLI promoted only `repair` with exit code 0. The checkout remained clean.
- unfiltered upstream disclosure: 71 passed and 29 failed because optional
  credentialed embedding/judge, LiteLLM, and SciPy tests were invoked without
  those credentials/extras. ProofGrid neither changes nor claims those paths;
  the deterministic reused modules are included in the 19-test passing gate.
- observation extension: 23 focused/reused-foundation tests pass; the same
  existing Starlette TestClient deprecation warning remains;
- interop: `CONTEXTSIDECAR_PROOFGRID_INTEROP_PASS calls=30 observations=30
  reviews=30 winner=fast-path`;
- observation package/static: Black, isort, Flake8, compileall,
  `git diff --check`, sdist/wheel build, and Twine checks pass.

## Known boundaries

- no named provider was evaluated; the paid/provider boundary was local-stub
  tested only;
- optional model-judge scores are not ground truth and are disabled by default;
- SQLite and the local server are single-process, not multi-tenant or
  production-scale infrastructure;
- deterministic latency is a local orchestration measurement and should not be
  compared with network model latency;
- provider token counts remain null when omitted; cost remains null unless
  reported token counts and explicit price inputs both exist;
- the six heldout cases are deliberately small and do not establish general
  extraction accuracy;
- no remote, push, deployment, client data, client outcome, or visual polish.
- no real answer provider was ranked; interop latency, reviews, and prices are
  local fixtures;
- answer observation review currently has CLI/API support, not a dedicated
  browser review interface.

## Exact next action

Integrate the shared-verification extension into ProofGrid and FirstRing local
`main` branches and update the central toolbox checkpoint. Hosted GitHub
execution remains a separately deferred receipt. ContextSidecar remains under
its separate owner; do not turn this extension into another evaluation control
plane or claim fixture evidence as provider quality.

## Technique-ceiling dossier closure — 2026-08-04

- Research exit gate: `PASS`; ProofGrid technique experiments remain
  `PARTIAL`.
- Isolated worktree: `portfolio_demos/worktrees/proofgrid_technique_dossier`.
- Branch: `agent/proofgrid-technique-dossier`, based on clean ProofGrid `main`
  commit `db5fbeef4eb64504d067f36561677d2b99a32925`.
- Dossier commit: `e8fe8850e51f32ce17dc389d0a162ff86ddcd713`.
- Required artifacts: `TECHNIQUE_TAXONOMY.md`, `EVIDENCE_MATRIX.csv`,
  `GITHUB_IMPLEMENTATION_AUDIT.md`, `BENCHMARK_DESIGN.md`,
  `RESEARCH_DECISION.md`, and the expanded `docs/EXPERTISE_NOTES.md`.
- Expertise disposition: central cards **Calibrate the evaluator before
  trusting the score** and **Report uncertainty before promoting a model
  change** were added to `UPWORK_EXPERTISE_INDEX.md`. Structured validity,
  scorer-call compatibility, retry classification and application-boundary
  notes explicitly reuse existing cards.
- Verification: all six artifacts exist; the CSV imports as 24 candidates with
  all required columns and no blank candidate/status/disposition; all eleven
  systematic evidence rows are `PASS`; `git diff --check` passes. Local
  evidence references resolve. Application tests were not rerun because this
  slice changes research/checkpoint Markdown and CSV only.
- Decision: retain AutoEvals as the focused scorer foundation and ProofGrid as
  the evaluation/control plane. Admit PG0 blinded human calibration, judge-bias
  probes, repeated paired evidence and uncertainty first. PG1 structured
  output, PG2 metamorphic relations and PG3 framework adapters remain gated.
- Scope stopped before: provider/judge calls, human-label collection,
  experiment execution, component integration, ContextSidecar work, UI/visual
  polish, merge, push or deployment.
- Exact next cross-portfolio action: complete the joint Relay + Website
  Assistant systematic dossiers in their own isolated worktrees. Do not start
  ProofGrid PG0 from this checkpoint. ContextSidecar is complete under another
  owner and outside this stream.
