# ProofGrid technique taxonomy

Date: 2026-08-04

## Decision boundary

ProofGrid evaluates application/model candidates against frozen acceptance
contracts. This dossier covers case design, executable and model-based scoring,
structured outputs, uncertainty, human calibration, robustness, statistics,
reproducibility and framework reuse. It does not rank a current provider,
create generic model leaderboards, replace application-specific capture, or
implement the admitted experiment.

## Problem decomposition

| Layer | Independent decision | Serious method families | Current ProofGrid boundary |
| --- | --- | --- | --- |
| outcome contract | define observable client success and prohibited behavior | exact target; executable state; rubric dimensions; pairwise preference; safety invariants | frozen schema/expected output and answer rubric |
| case acquisition | collect representative inputs and failures | production traces; expert authored; public benchmark; adversarial/fault generated; synthetic augmentation | JSONL/CSV plus one application observation contract |
| data lifecycle | prevent leakage and stale/saturated evidence | held-out family split; temporal/private set; dynamic/metamorphic variants; contamination checks | train/heldout label and content hashes; no contamination protocol |
| candidate execution | run equivalent candidate inputs | direct provider; local model; application adapter; agent/sandbox task | deterministic and OpenAI-compatible adapters plus imported application streams |
| structure enforcement | produce machine-consumable output | prompt-only; provider-native schema; grammar/constrained decoding; parse-and-retry; repair | unconstrained deterministic fixtures plus bounded repair path |
| syntactic validation | check format/schema | parser; JSON Schema; grammar coverage; official schema test suite | AutoEvals `ValidJSON` / jsonschema |
| semantic/executable scoring | check task truth | exact/diff; typed/business rules; code/tests/simulator state; reference metrics | exact and JSON diff; imported human rubric |
| rubric judgment | score open outputs | pointwise rubric; pairwise; listwise; reference-based; checklist/error taxonomy | optional single rubric judge, disabled without credentials |
| judge validity | determine whether automated judgment matches target people | blind human calibration; inter-rater reliability; criterion-specific agreement; bias probes | uncalibrated optional judge; fixture review only |
| uncertainty | quantify result and judge uncertainty | bootstrap/Wilson intervals; repeated stochastic trials; calibration/Brier/ECE; conformal sets; disagreement triage | scalar aggregates; no confidence interval or repeated-run policy |
| robustness | test invariants rather than only fixed answers | metamorphic relations; prompt paraphrase; position/order swap; verbosity/style; perturbation/fault injection | limited frozen edge cases and provider fault stubs |
| aggregation/decision | turn rows into a gate or ranking | hard acceptance gates; Pareto/risk-cost; paired tests; Bayesian/conformal ranking; Elo | hard thresholds then cost/retry/latency tie-break |
| human review | adjudicate ambiguity and improve rubric | blinded independent labels; disagreement adjudication; correction; error taxonomy | persisted review/correction; no blind multi-rater study |
| observability/reproducibility | preserve complete experiment identity | case/prompt/schema/model hashes; seeds/decoding; traces; environment; re-scoring; export | strong hashes, result JSON/CSV, provider usage/failure fields |
| security and privacy | contain untrusted outputs/tools and sensitive traces | sandbox; redaction; access/retention; prompt-injection/red-team suites | bounded import/privacy checks; no sandboxed agent execution |

## Technique families and operating regions

### Deterministic executable evaluation — `established`

Exact/schema checks, business invariants, tests, compilers and simulator state
are the highest-precision oracle when success can be made observable. They are
cheap, reproducible and explainable, but cannot directly grade every valid
open-ended answer. Proxy state-based agent evaluation reinforces that a richer
executable state can outperform vague end-text judging when the environment is
specified.

### Reference metrics and similarity — `established but bounded`

String distance, token overlap, embeddings and structured diffs are useful for
partial credit and retrieval/translation/summarization regions. They can reward
surface overlap without task truth. ProofGrid should treat them as diagnostic
dimensions or gates validated on the target task, never generic correctness.

### Native or grammar-constrained structured output — `established family`

JSONSchemaBench separates schema-feature coverage, compilation/mask overhead,
generation speed and semantic quality across native APIs and Guidance,
Outlines, llama.cpp and XGrammar-style engines. Constraint compliance is not
semantic support: some evidence reports accuracy degradation for
instruction-tuned models under constraints. Provider-native, Outlines and
XGrammar are distinct deployment profiles, not guaranteed quality upgrades.

### Parse/retry and bounded repair — `established fallback`, `contested default`

Validation feedback and retry can recover malformed output; deterministic
repair is defensible only where the intended value is unambiguous. Repair can
silently change meaning, and repeated generation adds cost and selection bias.
The current fixture proves one bounded ambiguous-date refusal rule, not generic
semantic repair.

### Pointwise rubric judge — `established provisional instrument`

A judge scores one output against explicit criteria/reference. It avoids some
pairwise comparison effects and supports qualitative error analysis, but
agreement varies strongly by criterion, task, expertise, prompt and model.
JUDGE-BENCH, LongJudgeBench and prompt-paraphrase studies reject one universal
judge accuracy claim.

### Pairwise/listwise judge — `established but bias-sensitive`

Pairwise judgment can increase discrimination and system ranking, but position,
length, style and self-preference can reverse choices. Order swapping and
pointwise-first reasoning are controls, not proof that bias is eliminated.

### Calibrated judge and selective human review — `established need`

Small human-labelled calibration sets, rubric feature heads, linear probes,
conformal sets or disagreement can route low-confidence cases to people.
Criterion-specific evidence matters more than a generic judge brand. Exact
winner and lowest-cost method for ProofGrid remain unresolved.

### Multi-judge panels/meta-judges — `contested`

Panels may expose disagreement, but multiple models can share correlated
errors; debate can amplify position, verbosity, chain-of-thought and bandwagon
bias. A panel is admitted only when it improves blind human agreement and
selective risk enough to pay its cost over one calibrated judge.

### Metamorphic and adversarial evaluation — `established family`, `provisional relations`

When exact oracles are incomplete, necessary relations across meaning-
preserving transformations test robustness: order swaps, prompt paraphrases,
irrelevant context, formatting/style, equivalent schemas and input
perturbations. Relations must be domain-reviewed because a supposedly invariant
transformation can legitimately change the answer.

### Repeated stochastic and uncertainty-aware comparison — `established need`

Temperature zero and a seed do not ensure identical provider output. Repeated
paired trials plus bootstrap/Wilson intervals distinguish a measured win from
noise; judge calibration and conformal/abstention methods expose uncertain
decisions. Small deterministic suites still need case-sampling uncertainty.

### Dynamic/contamination-resistant cases — `established benchmark concern`

Public static benchmarks can leak or saturate. Temporal/private cases,
versioned production failures and generated metamorphic variants reduce this
risk. Contamination detectors themselves have weak assumptions, so a claimed
clean public benchmark is not equivalent to a client acceptance set.

## Benchmark and evidence map

| Question | Public evidence | ProofGrid limitation |
| --- | --- | --- |
| schema coverage and decoding cost | JSONSchemaBench, official JSON Schema Test Suite | structure coverage is not application value correctness |
| multi-format structural generation | SoEval, StructEval, SO-Bench | broad format scores exceed current JSON extraction outcome |
| judge-human agreement | JUDGE-BENCH, JuStRank, LongJudgeBench | agreement is criterion/domain/rater-population specific |
| judge bias | LLMBar/MT-Bench derivatives, position/self/length/prompt studies | probes must be adapted to ProofGrid rubrics and outputs |
| open-ended application quality | human rubric sets such as SummEval and task-specific expert labels | expert truth and disagreement remain costly |
| reproducibility/uncertainty | repeated-evaluation studies, bootstrap/clustered errors, calibration work | current six heldout cases have no uncertainty estimate |
| robustness without exact oracle | metamorphic-testing survey and task-specific relations | relations require application owners and negative controls |
| contamination/saturation | dynamic-benchmark and contamination surveys | private temporal cases are stronger than detection guesses |
| agent/application execution | Inspect tasks/sandboxes and proxy-state agent evaluation | belongs behind application adapters, not one generic text runner |
| local acceptance | 18 deterministic extraction cases and imported stream contract | too small and fixture-authored for provider or judge claims |

## Search protocol

- Search date: 2026-08-04.
- Window: prioritize 2024–2026 surveys, benchmarks and maintained
  implementations; retain older seminal work only to define a family.
- Sites: ACL Anthology, OpenReview/PMLR, arXiv paper records, official project
  documentation and GitHub repository/API data.
- Inclusion: reproducible task/metric definition, human or executable truth,
  contrary evidence, resource detail, public code/data, or a maintained
  integration surface.
- Exclusion: vendor/blog claims without a protocol, generic leaderboards,
  unavailable implementation detail, license comparisons, and unrelated model
  capability scores.
- Evidence reuse: external results close family existence and known failure
  claims; ProofGrid benchmarks only transfer-sensitive calibration,
  composition, host/cost and application-routing questions.

### Reproducible query iterations

| Iteration | Query families | New decision-relevant families |
| ---: | --- | --- |
| 0 | `LLM evaluation systematic survey metrics reliability`; `LLM-as-judge survey` | full evaluation lifecycle and judge families |
| 1 | `JSONSchemaBench structured output constrained decoding`; `semantic structured output benchmark` | native/grammar constraints versus retry/repair |
| 2 | `judge benchmark human agreement position verbosity self preference` | pointwise/pairwise bias and meta-evaluation |
| 3 | `judge uncertainty calibration conformal human review` | calibrated selective review and uncertainty layer |
| 4 | official framework/GitHub audit for AutoEvals, Inspect, Promptfoo, DeepEval, OpenAI Evals, lm-eval-harness, JSONSchemaBench, Outlines, Guidance and XGrammar | implementation profiles, no new method family |
| 5 | `metamorphic testing LLM survey robustness prompt paraphrase`; `repeated stochastic evaluation` | metamorphic relations and repeated paired trials |
| 6 | `benchmark contamination dynamic saturation leakage survey` | dataset lifecycle detail; no new evaluator family |
| 7 | contrary studies on pairwise judges, multi-judge panels, long-form judges, constrained-decoding degradation and contamination detectors | no new family; failure boundaries only |
| 8 | 2026 survey/reference expansion across agents, rubrics, qualitative judges, structured output and reproducibility | no new family; compositions only |

Iterations 7 and 8 added no decision-relevant family. The search therefore
meets the two-consecutive-expansion saturation rule.

## Primary anchors

- [Critical LLM evaluation survey](https://aclanthology.org/2024.emnlp-main.764/)
- [LLM-as-a-judge survey](https://aclanthology.org/2025.emnlp-main.138/)
- [JUDGE-BENCH](https://aclanthology.org/2025.acl-short.20/)
- [JuStRank](https://aclanthology.org/2025.acl-long.34/)
- [Position-bias study](https://aclanthology.org/2025.ijcnlp-long.18/)
- [Prompt-variation robustness](https://aclanthology.org/2026.findings-acl.1929/)
- [LongJudgeBench](https://arxiv.org/abs/2606.01629)
- [JSONSchemaBench](https://arxiv.org/abs/2501.10868)
- [Hidden cost of constrained decoding](https://aclanthology.org/2025.ranlp-1.124/)
- [Metamorphic-testing survey](https://arxiv.org/abs/2605.13898)
- [Reproducible evaluation uncertainty](https://arxiv.org/abs/2410.03492)
- [Benchmark contamination survey](https://aclanthology.org/2025.emnlp-main.511/)
