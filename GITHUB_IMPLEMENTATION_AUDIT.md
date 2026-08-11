# ProofGrid GitHub implementation audit

Date checked: 2026-08-04

## Rule and baseline

GitHub was checked before designing any substantial scorer, harness,
structured-decoding, calibration, statistical or metamorphic subsystem. Reuse
must remove one complete responsibility behind ProofGrid's case/result/review
contracts. Whole frameworks that replace the runner, store, API, UI and gate
are rejected. Tiny adapters, project-specific relations and acceptance rules
remain local when reuse creates more integration than behavior.

- baseline: clean `main` at
  `db5fbeef4eb64504d067f36561677d2b99a32925`;
- host: CPU, 32 GB RAM, no NVIDIA runtime detected;
- existing foundation: AutoEvals `Score`, `ValidJSON`, `JSONDiff`,
  `ExactMatch` and optional rubric/provider seams;
- existing ProofGrid surfaces: versioned case/candidate/schema/promotion hashes,
  deterministic and OpenAI-compatible adapters, SQLite review, API/CLI/CSV,
  application observation import and hard promotion gates.

## Framework snapshot

| Repository | Pin / release | Current health and defects | Reusable surface | Decision |
| --- | --- | --- | --- | --- |
| `braintrustdata/autoevals` | `b0e1055892bea1305a10f8d42fdc47ff1b41ffa4`; js-0.3.0 | pushed 2026-07-29; 19 open issues | focused dual-language scorer contracts, JSON/exact/similarity and rubric judges | retain foundation; verify every concrete call contract |
| `UKGovernmentBEIS/inspect_ai` | `cb00efcd12dfbf3e44f486648e05e54f1337fe9a` | pushed 2026-08-04; 259 open issues; #4742 reports numeric matching with punctuation | dataset/solver/scorer task model, sandboxes, limits, logs, re-scoring, clustered errors, agent/tool evaluation | adopt an import/export or task adapter only when executable/agent workload activates; no migration |
| `promptfoo/promptfoo` | `7b898cbdb16205cb7f0e2994baa807d131eb2326`; 0.122.0 | pushed 2026-08-04; 478 open issues; #10298 reports Azure evaluator authentication failure | provider/prompt matrix, assertions, CI, reports and red-team generation | reject whole framework; use configuration/red-team patterns as references |
| `confident-ai/deepeval` | `e2bf78ef5ae4ad4c1ea34915d86734ecc376dce8`; v4.1.5 | pushed 2026-08-04; 422 open issues; #3000 GEval logprob parsing, #2998 shared optimizer state, #2993 invalid default model | pytest integration, broad judge/RAG/agent metrics, tracing and datasets | do not import metric catalog without target human calibration; focused adapter only if one metric wins |
| `openai/evals` | `8eac7a7de5215c907fbddc30efdaf316913eccdd` | pushed 2026-04-14; 219 open issues; no current release returned | registry and eval/model-graded patterns | reference only; narrower current fit than retained foundation plus Inspect seam |
| `EleutherAI/lm-evaluation-harness` | `f4d4b3de3ee6741a7151a9fe74945ee515262f4c`; v0.4.12 | pushed 2026-07-13; 932 open issues; #3966 reports incorrect zero stderr; #3964 flags old sqlitedict | reproducible model task registry and public benchmark execution | adapter only for a selected capability benchmark; not application evaluation core |

## Structured-output snapshot

| Repository | Pin / release | Current health and defects | Reusable surface | Decision |
| --- | --- | --- | --- | --- |
| `guidance-ai/jsonschemabench` | `ba103c73756198dd9b149ddc7db7867da7a077f6` | pushed 2026-02-12; 3 open issues; no release | 10K real schemas, official-test-suite bridge, coverage/compile/mask/generation measurements | adopt benchmark data/runner interface for a bounded schema subset; do not copy results |
| `dottxt-ai/outlines` | `9b8d2560ad3262d17a779d7dfb28505586a1d36c`; 1.3.2 | pushed 2026-08-03; 131 open issues; current Optional, additionalProperties and regex-container defects | local constrained generation across backends | first local-engine candidate only after a local model profile exists; pin and run unsupported-schema failures |
| `microsoft/guidance` | `21b1d90dfbebff4b141df70c714c8af15aa5f4af`; 0.3.2 | pushed 2026-05-21; 316 open issues; URI validation, dict-schema and stop-string defects | generation DSL and schema/grammar control | reject first integration; broader DSL and current defects exceed the bounded need |
| `mlc-ai/xgrammar` | `ac23bccdf191f5bd68b328882431937dc15319b9`; v0.2.5 | pushed 2026-08-03; 59 open issues; XML loop, string-schema escape and macOS import defects | high-performance grammar compiler/mask and server integrations | server/runtime candidate only; not a standalone ProofGrid responsibility |

## Component decisions

| Proposed responsibility | Reuse decision | Exact seam | Cost decision |
| --- | --- | --- | --- |
| deterministic schema/exact/diff | retain AutoEvals | `_evaluate_output` normalizes inputs into existing scorer calls | already proven and smaller than framework migration |
| executable/state scoring | refit Inspect task/log contract later | adapter maps ProofGrid case IDs and candidate versions to Inspect task/log/score artifacts | removes sandbox/task execution when activated without replacing review/gate |
| native/provider structured output | refit existing provider adapter | common JSON Schema subset and provider capability metadata | no new framework needed for hosted APIs |
| local constrained decoding | adopt Outlines or XGrammar through the chosen model server only | one candidate adapter; schema compile, supported-feature report and raw output retained | do not integrate an engine without a selected local model/runtime |
| JSONSchemaBench coverage | adopt bounded benchmark runner/data | stratified schemas and official-suite feature categories feed ProofGrid cases | prevents writing schema coverage cases; full 10K run is unnecessary for first seam |
| rubric judge | retain AutoEvals judge call; add calibration around outputs | blinded judge ID, rubric/version, raw decision/reason and confidence features | DeepEval/Promptfoo do not establish criterion validity automatically |
| bias probes | custom bounded case transformations | order swap, length/style controls, rubric paraphrases and self-family label masking | domain-specific relations are small; no imported framework removes their truth review |
| intervals/calibration | use standard scipy/sklearn/statsmodels primitives if authorized | per-case paired rows in; bootstrap/Wilson/Brier/ECE/risk-coverage out | do not build statistics formulas from scratch; do not import an MLOps platform |
| human calibration | extend existing review record | blinded rater assignment, rubric, labels, disagreement/adjudication | application-specific workflow over existing store; framework adoption would duplicate storage |
| metamorphic registry | custom relation manifest over existing cases | source case, transform version, expected invariant/change and negative control | relation semantics are the owned behavior; generic generation is not the oracle |
| public benchmark execution | lm-eval or Inspect adapter only after task selection | preserve upstream task revision/config and import raw sample scores | avoids reimplementing benchmark runners; no generic leaderboard |
| red-team generation | Promptfoo patterns or adapter only for a selected threat suite | generated cases must be reviewed/frozen before promotion evidence | broad red-team product is outside first ProofGrid experiment |

## Minimal future integration check

For any adopted component:

1. pin code/package/model and record environment plus schema/task revision;
2. pass one supported case and one known unsupported/failure case through the
   existing case/result contract before changing orchestration;
3. retain raw outputs, scorer/judge identity, usage/cost and error class;
4. compare with the unchanged AutoEvals/ProofGrid control;
5. prove review, export and gate recomputation still work; and
6. remove the component if the seam requires replacing ProofGrid-owned runner,
   store or product workflow.

## Conclusion

No substantial subsystem needs to be authored from scratch. ProofGrid should
remain a small application evaluation/control plane over focused scorers and
adapters. The first research experiment needs standard statistical primitives,
existing review storage and bounded bias transformations—not a second
evaluation platform.
