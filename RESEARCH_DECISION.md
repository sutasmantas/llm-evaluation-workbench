# ProofGrid research decision

Date: 2026-08-04

## Decision

The systematic dossier is `PASS`; ProofGrid's technique-ceiling experiment
gate remains `PARTIAL`. No experiment or implementation was run.

Retain AutoEvals as the focused scorer foundation and ProofGrid as the
application evaluation/control plane. The first experiment is PG0: validate a
pointwise rubric judge and its uncertainty against blinded human labels,
deterministic seeded faults, repeated trials and bias perturbations. Structured
output engines, metamorphic relations and framework adapters remain separately
gated.

## Retained families

| Family | Status | Role |
| --- | --- | --- |
| executable/schema/exact/business scorers | `established` | first choice when success is observable |
| similarity/diff metrics | `established but bounded` | diagnostic/partial-credit dimension only |
| provider-native and grammar constraints | `established family`, `provisional fit` | PG1 candidates; validity is not semantic correctness |
| bounded repair | `established locally`, `contested default` | narrow control; no generic semantic repair claim |
| pointwise rubric judge | `provisional instrument` | PG0 automated control after blind rubric |
| pairwise judge/order swap | `established but bias-sensitive` | close-candidate challenger and bias probe |
| calibrated judge/selective review | `established need`, `unknown winner` | PG0 target |
| multi-judge/meta-judge | `contested` | conditional only if one calibrated judge misses gate |
| bootstrap/repeated trials | `established need` | shared uncertainty layer |
| metamorphic testing | `established family`, `provisional relations` | PG2 cross-project robustness |
| dynamic/private cases | `established benchmark concern` | later suite lifecycle, not a contamination guarantee |

## Framework decision

- Keep AutoEvals's narrow scorer contracts.
- Reuse Inspect only through a future executable/agent task-log adapter; do not
  migrate ProofGrid's runner, store, review or UI.
- Reuse a bounded JSONSchemaBench subset for PG1 rather than authoring schema
  coverage cases.
- Select Outlines or XGrammar only with a concrete local/server model profile.
- Do not adopt Promptfoo, DeepEval, OpenAI Evals or lm-evaluation-harness as a
  replacement application. Their useful focused task/metric surfaces remain in
  the audit for failure-driven reuse.

## External answers and unresolved questions

| Question | Evidence disposition | Result |
| --- | --- | --- |
| Does valid JSON establish correct values? | external and local evidence | closed `no` |
| Should executable truth precede model judging? | external architecture and task evidence | closed `yes` where observable |
| Is one uncalibrated judge ground truth? | multiple meta-evaluations | closed `no` |
| Does a judge panel automatically fix bias? | contrary panel/debate/correlation evidence | closed `no` |
| Are repeated runs and intervals necessary? | reproducibility evidence | closed `yes` for stochastic/provider comparisons |
| Which judge/rubric fits portfolio decisions? | criterion/rater/task-specific | unresolved; PG0 |
| Does calibration reduce selective risk enough to automate? | recent methods, no transferable threshold | unresolved; PG0 |
| Which structured-output path is non-dominated? | runtime/model/schema specific | unresolved; PG1 |
| Which metamorphic relations are valid across projects? | application-specific truth | unresolved; PG2 |

## Systematic evidence gate

| Gate | Evidence | Status |
| --- | --- | --- |
| Problem decomposition | fifteen independent layers in `TECHNIQUE_TAXONOMY.md` | PASS |
| Search protocol | date, sources, window, rules and nine query iterations recorded | PASS |
| Survey coverage | 2024 critical evaluation, 2025 judge, 2025 contamination and 2026 metamorphic/agent evaluation surveys | PASS |
| Benchmark coverage | schema/structure, judge-human agreement, bias, long-form, uncertainty, robustness, contamination and local acceptance map | PASS |
| Existing-answer search | each major question has an external/local closure or unresolved experiment disposition | PASS |
| Technique-family saturation | iterations 7 and 8 added no decision-relevant family | PASS |
| Candidate comparison | `EVIDENCE_MATRIX.csv` covers methods, frameworks, resources, maintenance and failure modes | PASS |
| Contrary evidence | constrained-decoding degradation, judge variability/bias, panel correlation, contamination-detector weakness and stochastic instability recorded | PASS |
| Implementation evidence | `GITHUB_IMPLEMENTATION_AUDIT.md` pins ten repositories, open defects, runnable seams and adoption boundaries | PASS |
| Portfolio fit | shared measurement, structured output, agent execution and robustness have non-duplicative activation conditions | PASS |
| Review status | every conclusion is labelled; only explicit PG0–PG3 designs enter the queue | PASS |

## Expertise extraction

- Canonical notes: `docs/EXPERTISE_NOTES.md`.
- Central card to add: **Calibrate the evaluator before trusting the score**.
- Central card to add: **Report uncertainty before promoting a model change**.
- The structured-validity note remains covered by existing **Validate semantic
  support separately from JSON shape**; framework-call and retry notes remain
  covered by their existing cards. Those dispositions are explicit locally.

## Boundary and next action

This dossier may authorize a later isolated PG0 experiment only after the
portfolio checkpoint accepts it. It does not authorize paid calls, human-label
collection, structured-decoding integration, framework migration, visual
polish, ContextSidecar work, or the next project's dossier.
