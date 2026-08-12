# ProofGrid expertise notes

**Verification:** [claim-to-artifact map and rerun commands](https://sutasmantas.github.io/evidence/#proofgrid) · [machine-readable receipt](https://sutasmantas.github.io/evidence/receipt.json)

**Shared-boundary evidence:** ProofGrid owns two narrow `0.1.0` wheels for a
vendor-neutral completion/replay contract and strict schema-conformant output.
The package suites use construction-known response/transport faults, and an
eight-mutant source gate proves the checks can reject the admitted defect
classes. Relay consumes the exact wheels without installing the full workbench;
native tool calling, streaming and provider-specific CLI behavior remain out of
scope.

## Experiment 1 — structured validity is not semantic support

- failure symptom: the schema-constrained path returned valid JSON for the
  relative phrase “next Friday” but invented `2026-08-07`, while the frozen
  expected result required `null` because the reference date/timezone was not
  supported.
- diagnosis: output-shape validation and field-support correctness are
  independent controls. A schema can prevent malformed output without
  preventing an unsupported value.
- options compared: loose baseline extraction; schema-constrained extraction;
  schema-constrained output plus a bounded repair rule for ambiguous relative
  dates.
- decision rule: on heldout cases require schema pass rate 1.0, exact pass rate
  at least 0.95, mean structured similarity at least 0.95, zero unresolved
  reviews, and zero exhausted/permanent provider failures. Passing candidates
  are ordered by cost, retries, latency, then stable candidate ID.
- control: all three paths ran over the same 18 frozen cases, including the
  same 6 heldout cases; candidate prompts/configs, schema, suite, and promotion
  rule are content-hashed. The rule was committed before the evidence run.
- evidence: baseline heldout schema/exact/task = 0.0/0.0/0.639384;
  structured = 1.0/0.833333/0.972222 with one open review; repair =
  1.0/1.0/1.0 with zero open reviews and one deterministic simulated
  rate-limit retry. Only repair was promoted.
- client relevance: a proposal can promise a concrete acceptance gate and
  correction workflow without implying that “JSON mode” alone makes an
  extraction system reliable.

## Experiment 2 — integrating a scorer requires testing its real call contract

- failure symptom: the first actual run raised `TypeError` when the schema was
  supplied as a keyword, and exact comparisons could differ only because JSON
  object keys were serialized in another order.
- diagnosis: the reused scorer abstraction and its concrete implementations
  have different parameter names, while exact comparison is serialization
  sensitive.
- options compared: copy/rewrite the scorers; call undocumented internal
  methods; adapt at a narrow boundary and retain the upstream implementation.
- decision rule: keep central upstream behavior, normalize inputs before the
  scorer, and regression-test every compatibility adaptation.
- control: deterministic AutoEvals JSON/serialization tests run beside the
  ProofGrid integration tests; canonical hashes prove stable object ordering.
- evidence: 19 focused/reused-foundation tests pass, including schema-valid but
  semantically wrong output and stable canonicalization cases.
- client relevance: third-party evaluation libraries reduce delivery time only
  when their executable contracts—not README examples alone—are verified in
  the target runtime.

## Experiment 3 — retry only failures that can plausibly recover

- failure symptom: a provider can return a rate limit or server failure during
  an otherwise valid batch; retrying every error hides permanent request
  defects and increases cost/latency.
- diagnosis: transport/provider failures need a normalized transient versus
  permanent classification before retry policy is applied.
- options compared: no retry; retry every failure; bounded retry for 429/5xx
  and transport errors while refusing permanent 4xx failures.
- decision rule: retry transient failures up to the configured budget, count
  each retry/rate limit, and route exhausted or permanent failures to review
  with no fabricated output.
- control: a local OpenAI-compatible stub returns 429 then success with a usage
  block; a second case returns 400. No paid provider or network-quality claim
  is involved.
- evidence: the 429 case records one retry, one rate limit, 17 reported tokens,
  and computed configured cost; the 400 case records a permanent failure and
  zero retries.
- client relevance: the adapter can be scoped in a proposal as tested failure
  behavior, while production retry budgets and provider-specific error maps
  remain client configuration work.

## Experiment 4 — evaluate the real application boundary without cloning the evaluator

- failure symptom: ContextSidecar needed streamed-delta and first-useful
  measurements, but its first runner also began accumulating generic review,
  cost, summary, and candidate-decision code already owned by ProofGrid.
- diagnosis: provider-path capture and evaluation orchestration are different
  responsibilities. A generic framework cannot infer the desktop app's exact
  streamed events, while the desktop app should not own another evaluation
  database and comparison engine.
- options compared: keep a bespoke ContextSidecar benchmark; add Promptfoo or
  Evalite to the Electron project; bridge the small application-specific
  observation contract into the existing ProofGrid/AutoEvals workbench.
- decision rule: ContextSidecar owns only message construction, the production
  provider call, safe stream/timing/usage capture, and frozen-source hashes.
  ProofGrid owns validation, sourced cost, AutoEvals `Score`, review history,
  summaries, gates, exports, and winner selection.
- control: two candidates must carry identical corpus, replay-contract,
  context-pack, and ordered case IDs. Outputs must reconstruct exactly from
  monotonic deltas. First-useful time is derived only from a reviewer-selected
  observed delta.
- evidence: 23 focused/reused-foundation tests pass. The local cross-repository
  proof made 30 production-adapter mock calls, imported 30 observations,
  persisted/resolved 30 reviews, and selected the faster/cheaper passing fixture
  without persisting the provider key.
- client relevance: the same workbench can now evaluate outputs from an
  existing chatbot/copilot code path instead of forcing a client to replace
  their provider layer or accept a separate untested benchmark implementation.

---

# ProofGrid technique-ceiling expertise notes

Date: 2026-08-04

## Calibrate the evaluator before trusting the score

### Client trigger

- Job wording: LLM-as-a-judge, automated quality scoring, prompt/model
  comparison, regression gate, human evaluation, or rubric-based review.
- Delivery condition: open-ended outputs cannot be fully checked by code, so an
  automated judge would influence release or routing.

### Failure symptom or unanswered choice

A judge can return clean numerical scores and explanations while disagreeing
with the target reviewers. Evidence across tasks shows criterion-dependent
agreement, position/length/self-preference, prompt sensitivity and repeated-run
instability. Adding more judges can preserve correlated errors or amplify bias.

### Competing options and evidence reuse

| Option | Evidence status | Main tradeoff |
| --- | --- | --- |
| deterministic/executable scorer | established where behavior is observable | high precision but incomplete for open quality |
| one pointwise rubric judge | provisional instrument | cheapest semantic judge; validity is task-specific |
| pairwise judge with order swap | established but bias-sensitive | discrimination versus position/style/non-transitivity |
| calibrated judge + selective review | established need, winner unresolved | human labels and calibration work versus lower review risk |
| multi-judge/meta-judge | contested | more signal and cost, but correlated errors remain |

External studies close that no uncalibrated judge or panel is universal. They
cannot select ProofGrid's rubric, judge or threshold because the target rater
population and criteria differ. That applicability question requires PG0.

### Decision rule

Use executable truth first. For remaining criteria, freeze a blind human
rubric and calibration/test split before judge calls. Promote the simplest
judge policy only when it meets criterion-level human agreement, seeded-fault,
bias-stability, false-pass and selective-risk gates with uncertainty bounds.
Otherwise keep human review.

### Delivery control and reuse boundary

Version judge/model/rubric, randomization, repeats and raw reasoning/decision.
Keep reviewer disagreements and criterion prevalence. Revalidate after judge,
rubric, task, language or target-reviewer changes. ProofGrid owns calibration,
review and release policy; an application owns its exact capture and truth
contract. A future adopted judge implementation must pass the existing
case/result/review interface and one success/failure integration check.

### Proposal-safe insight

I do not treat an LLM judge score as ground truth. I validate each rubric
criterion against blinded human labels, probe order/style/repeat instability,
and route low-confidence cases to review before the score can gate a release.

### Evidence and interview follow-up

- Evidence: `TECHNIQUE_TAXONOMY.md`, `EVIDENCE_MATRIX.csv`,
  `BENCHMARK_DESIGN.md` PG0 and `RESEARCH_DECISION.md`.
- Likely question: Why not use three judges and majority vote?
- Short answer: diversity helps only when errors are independent. I require the
  panel to beat one calibrated judge on blind human agreement and selective
  risk after accounting for cost; otherwise it is complexity without evidence.
- Central disposition: **new card** — `Calibrate the evaluator before trusting
  the score`.

## Report uncertainty before promoting a model change

### Client trigger

- Job wording: compare prompts/models/providers, regression testing, A/B
  evaluation, confidence intervals, or CI promotion thresholds.
- Delivery condition: model outputs or judges are stochastic, cases are sampled
  from a larger workload, or the apparent winner is close.

### Failure symptom or unanswered choice

A single aggregate score makes a small fixture set look exact. Even temperature
zero/provider seeds can vary, and case mix can reverse rankings. Picking the
highest mean without paired uncertainty turns noise and benchmark composition
into a release decision.

### Competing options

| Option | Benefit | Failure risk |
| --- | --- | --- |
| one deterministic run/mean | cheap and reproducible for pure code paths | ignores case-sampling and provider variance |
| repeated paired trials + bootstrap/Wilson bounds | interpretable and broadly reusable | inference cost and grouped-case assumptions |
| Bayesian/conformal ranking | richer probability/abstention decisions | more assumptions and calibration complexity |

### Decision rule

Keep deterministic gates exact. For stochastic candidates, run paired repeats
over the same ordered cases and report per-slice intervals. Promote only when
the paired interval excludes the predeclared material regression and all
critical hard gates pass. Use Bayesian/conformal machinery only if the simpler
interval and abstention policy cannot answer the delivery decision.

### Delivery control and reuse boundary

Record run count, ordering, seeds/decoding, provider revision, stopped/failed
runs and the sampling unit used for intervals. Cluster related variants by
source case. Never silently reduce repeats after seeing cost or results. The
statistical primitives should come from maintained libraries; ProofGrid owns
only the pairing, grouping and promotion policy.

### Proposal-safe insight

I report whether a candidate's improvement survives repeated paired cases and
uncertainty—not only its average score—and I keep correctness gates separate
from latency/cost tie-breaks.

### Evidence and interview follow-up

- Evidence: `BENCHMARK_DESIGN.md`, `EVIDENCE_MATRIX.csv` and the reproducible
  evaluation sources in `TECHNIQUE_TAXONOMY.md`.
- Likely question: Do deterministic test suites need confidence intervals?
- Short answer: the code result may be deterministic, but the selected cases
  still sample a workload. Exact critical gates remain binary; comparative
  claims need uncertainty over cases, and stochastic providers additionally
  need repeated runs.
- Central disposition: **new card** — `Report uncertainty before promoting a
  model change`.

## Technique-ceiling dispositions for existing notes

- **Experiment 1 — structured validity is not semantic support:** retained and
  externally reinforced; central disposition remains **duplicate** of
  `Validate semantic support separately from JSON shape`.
- **Experiment 2 — test the real scorer call contract:** retained; central
  disposition remains **duplicate** of `Verify an adapter at the wire before
  claiming the integration`.
- **Experiment 3 — retry only recoverable failures:** retained; central
  disposition remains **duplicate** of `Retry incomplete actions, not the
  entire workflow` and `Classify integration failures before retrying`.
- **Experiment 4 — evaluate the real application boundary:** retained as an
  adapter-design example but no new central card. It is too specific and
  overlaps the existing wire-verification and shared-evaluator cards. No
  ContextSidecar work or evidence reconciliation was performed in this dossier.
