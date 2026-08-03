# ContextSidecar observation integration

Date: 2026-08-03

## Purpose

ContextSidecar exercises its actual TypeScript provider and exports a bounded
`contextsidecar.answer-observations.v1` bundle. ProofGrid imports that evidence
and owns the reusable evaluation workflow: review persistence, rubric scoring,
first-useful timing, sourced cost, candidate comparison, and release gates.

This prevents the desktop application from growing a second evaluation
framework while making ProofGrid useful for application-path outputs that were
generated outside its own provider adapters.

## Import workflow

```powershell
.\.venv\Scripts\proofgrid.exe import-observations `
  --bundle .proofgrid\candidate-a.json `
  --bundle .proofgrid\candidate-b.json `
  --pricing .proofgrid\pricing.json `
  --db .proofgrid\runs.sqlite3 `
  --output .proofgrid\imported-run.json

.\.venv\Scripts\proofgrid.exe reviews `
  --db .proofgrid\runs.sqlite3 `
  --status open

.\.venv\Scripts\proofgrid.exe review-answer `
  --db .proofgrid\runs.sqlite3 `
  --review-id '<run:candidate:case>' `
  --review .proofgrid\one-review.json

.\.venv\Scripts\proofgrid.exe export `
  --db .proofgrid\runs.sqlite3 `
  --format csv `
  --output .proofgrid\answer-comparison.csv
```

Pricing is optional. When supplied, it must be explicit and sourced:

```json
{
  "candidate-a": {
    "input_per_million_usd": 1.0,
    "output_per_million_usd": 2.0,
    "source": "https://provider.example/pricing, accessed YYYY-MM-DD"
  }
}
```

Missing provider-reported tokens or missing pricing keeps cost `null`; it is
never converted to zero.

## Human rubric

Each successful answer review supplies exactly six integer scores from 0 to 2:

- addresses the question;
- uses only approved context;
- makes no unsupported claim;
- is concise enough for real-time use;
- has usable structure;
- clarifies when necessary.

The reused AutoEvals `Score` contract stores the normalized total and metadata.
A case passes at 9/12 or higher only when no dimension is zero. The reviewer
selects an observed stream delta; ProofGrid derives first-useful milliseconds
from that delta rather than accepting a typed timing value. Failed provider
observations can be reviewed but cannot receive a first-useful timestamp or
pass the rubric.

## Default comparison gate

The default gate is deliberately explicit and can be overridden by a versioned
promotion JSON object:

- case pass rate at least 0.80;
- zero unsupported-claim failures;
- zero provider failures;
- zero unresolved reviews;
- first-useful p95 no more than 3,000 ms.

At least two bundles with identical case, replay-contract, and context-pack
hashes are required before a winner can be selected. Passing candidates are
ordered by sourced cost when available, first-useful p95, completion p95, then
stable candidate ID. This is a comparison on the frozen application corpus,
not a general provider ranking.

## Validation and safety boundaries

The importer rejects:

- malformed or oversized bundles;
- a schema version other than `contextsidecar.answer-observations.v1`;
- privacy flags indicating a persisted key or full context;
- duplicate or reordered case IDs;
- candidates captured from different frozen inputs;
- non-monotonic streams, broken cumulative character counts, or outputs that
  do not equal the recorded stream;
- inconsistent success/error, timing, usage, and failure fields;
- missing or unsourced pricing entries when pricing is requested;
- incomplete/out-of-range rubrics and first-useful indexes outside the stream.

## Executable proof

```powershell
$env:CONTEXT_SIDECAR_ROOT='<ContextSidecar checkout>'
$env:PROOFGRID_PYTHON='<ProofGrid venv python>'
node scripts\verify_contextsidecar_interop.mjs
```

The 2026-08-03 local proof executed two 15-case candidates through
ContextSidecar's real streamed provider adapter, imported 30 observations,
persisted and resolved 30 reviews, recomputed both candidate gates, and selected
the faster/cheaper passing fixture path. The provider key was absent from the
captured and evaluated results. This proves the integration contract, not real
provider quality or latency.
