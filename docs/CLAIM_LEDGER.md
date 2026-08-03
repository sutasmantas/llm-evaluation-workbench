# ProofGrid claim ledger

## Allowed claims

| Claim | Evidence | Boundary |
| --- | --- | --- |
| Built a reusable LLM evaluation workbench with JSONL/CSV import, versioned runs, structured-output checks, review corrections, and CI/client exports | `py/proofgrid`, `proofgrid_web`, API/browser tests, committed JSON/CSV evidence | local single-process reference implementation |
| Compared baseline, schema-constrained, and repair paths on one frozen 18-case extraction/classification suite | `evals/proofgrid`, `docs/evidence/frozen-experiment.json` | 12 train and 6 heldout deterministic fixtures only |
| Pre-registered the promotion thresholds and promoted only the repair path in the initial run | `evals/proofgrid/promotion.json`; heldout repair schema/exact/task = 1.0/1.0/1.0; structured exact = 0.833333 | not a provider-quality claim |
| Records per-case quality, latency, token, cost, retry, rate-limit, failure, and review fields | JSON/CSV evidence and `test_frozen_experiment_promotes_only_repair_path` | token counts remain null when a provider does not report them; no-key cost is exactly USD 0 |
| Applies bounded retry to transient OpenAI-compatible failures and does not retry permanent 4xx failures | focused local-stub tests | proves adapter policy, not third-party uptime |
| Persists evidence-backed corrections and recomputes the promotion gate | SQLite store/API/browser correction test | single-process SQLite; no multi-user concurrency claim |
| Supports optional OpenAI-compatible candidates and rubric judge calls | explicit environment contract, adapter tests, missing-configuration test | no named provider was quality-tested and no live paid request was made |
| Imports application-path streamed answer observations and reuses the existing run/review/export gate | `py/proofgrid/observations.py`, store/API/CLI integration, 23 focused tests, `scripts/verify_contextsidecar_interop.mjs` | local two-candidate mock proof only; no real provider was ranked |
| Validates first-useful timing against an observed stream delta and stores the six-dimension human rubric through AutoEvals `Score` | observation tests plus 30-review cross-repository proof | the mock reviews are fixture assertions, not human quality evidence |

## Claims that are not supported

- no claim that one model or provider is superior;
- no claim that deterministic fixtures predict production accuracy;
- no claim that an LLM judge is ground truth;
- no hosted, production-scale, multi-tenant, authentication, or distributed
  execution claim;
- no client deployment, client data, conversion, revenue, or time-saving claim;
- no claim that the simulated no-key rate limit demonstrates a real provider's
  behavior;
- no claim that the built wheel bundles the demo UI and frozen suite; the
  verified quickstart is the source checkout.
- no claim that the existing structured-output browser matrix is an answer
  review UI; answer observations are currently supported through CLI and API.
