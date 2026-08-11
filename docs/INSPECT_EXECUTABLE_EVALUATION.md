# Inspect executable-evaluation boundary

## Decision

ProofGrid activates the Inspect AI adapter anticipated by the prior GitHub
implementation audit. The trigger is concrete: FirstRing has an executable
agent workflow with deterministic application outcomes that should be evaluated
without copying another harness into the consumer.

Inspect AI is pinned to commit
[`cb00efcd12dfbf3e44f486648e05e54f1337fe9a`](https://github.com/UKGovernmentBEIS/inspect_ai/commit/cb00efcd12dfbf3e44f486648e05e54f1337fe9a).
Its documented task model combines a dataset, solver, and scorer; every run
produces a sample-level evaluation log that can be rescored and inspected.
See the official [task](https://inspect.aisi.org.uk/tasks.html),
[scoring](https://inspect.aisi.org.uk/scoring.html), and
[log](https://inspect.aisi.org.uk/eval-logs.html) documentation.

## Ownership boundary

| Responsibility | Owner |
| --- | --- |
| task scheduling, sample execution, scorer invocation, raw log | Inspect AI |
| JSON-Schema oracle scorer, version checks, normalized decision | ProofGrid |
| executable scenario, fixture data, schema oracle | consumer project |
| application behavior and failure recovery | consumer application |

ProofGrid does not copy Inspect's runner, model adapters, viewer, retry engine,
or log format. Consumers do not copy ProofGrid's scorer or importer.

## Versioned contract

An import is rejected unless all of these hold:

1. the Inspect run completed successfully and includes samples;
2. task metadata declares `proofgrid.inspect-json-schema.v1`;
3. task metadata declares the exact audited Inspect commit;
4. the log records Inspect version `0.3.253.dev7+gcb00efcd1`;
5. every sample ID is unique and every sample has the required scorer;
6. every score is numeric and every sample is error-free; and
7. every score reaches the frozen threshold.

The oracle is construction-known JSON Schema, not an LLM judge. Each consumer
can assert exact outcomes, required events, metric bounds, and nested state
without teaching ProofGrid its business rules.

## Falsification evidence

The provider reference satisfies its schema and imports with a 1.0 pass rate.
FirstRing independently executes four real deterministic scenarios through the
same boundary. Its baseline passes 4/4. A fail-open mutation changes the
unknown-FAQ result from transfer to answered and removes its not-found/transfer
evidence; the shared contract rejects that case, leaves the other three green,
and makes `proofgrid import-inspect --require-pass` exit 2.

Evidence:

- `docs/evidence/inspect-reference/` in ProofGrid;
- `docs/evidence/inspect/baseline/` in FirstRing;
- `docs/evidence/inspect/fail-open-mutant/` in FirstRing.

Raw Inspect JSON logs and normalized ProofGrid results are retained. SQLite
runtime state is reproducible scratch data and is not evidence.

## Claim limits

This proves one pinned execution/log/scorer/import contract transfers from its
provider reference to FirstRing and detects the planted fail-open defect. It
does not establish real telephony quality, model/provider superiority,
production latency, general agent correctness, or fitness for unrelated oracle
types. Another consumer must bring its own executable workload and frozen
truth; it may reuse the boundary but not FirstRing's schemas.

The legacy `doc` and new `inspect` extras use incompatible upstream
`docstring-parser` ranges. `uv` records them as conflicting extras so each
environment remains locked instead of silently downgrading either tool.
