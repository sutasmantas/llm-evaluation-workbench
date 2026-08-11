# ProofGrid technique-ceiling benchmark design

Date: 2026-08-04

Status: design only. No provider call, component integration or experiment was
run in this dossier.

## Objective

Build the smallest trustworthy measurement spine the remaining portfolio
experiments can reuse. External evidence already closes that schema validity is
not semantic correctness, one LLM judge is not ground truth, panels are not an
automatic upgrade, and public static benchmarks do not replace application
cases. Local work is reserved for:

1. whether a specific rubric judge agrees with the portfolio's blinded human
   labels and remains stable under known bias transformations;
2. whether native constraints, grammar constraints or validation retry improve
   structured correctness under the same provider/model/task budget; and
3. whether repeated paired evidence changes a promotion decision.

## Common frozen protocol

Before code or paid calls, freeze:

- case IDs, source/ownership, task and failure categories, family/temporal
  split, expected observable behavior and prohibited behavior;
- candidate provider/model/revision, endpoint class, prompt, response mode,
  schema dialect, decoding parameters, retries and prices with dated sources;
- scorer/judge/rubric versions and raw outputs/reasons;
- run count, seeds where accepted, sample order randomization and stop rule;
- human rater population, blind assignment, adjudication and exclusion rules;
- resource/cost envelope and pre-registered promotion policy.

Never use the same cases to author/tune a rubric or repair rule and to report
its held-out performance. Split by source/application/failure family, not row.

## PG0 — measurement spine and calibrated judge

### Data

Use 120 frozen output artifacts without generating new candidate answers:

- 40 structured outputs containing valid-correct, valid-wrong, invalid-
  repairable and invalid-ambiguous strata;
- 40 short application answers covering grounded support, refusal, tool state
  and handoff outcomes from projects other than ContextSidecar;
- 40 open or longer answers with factual, relevance, instruction and style
  dimensions.

At least 30% must be seeded contrast pairs with one known changed property.
Keep 30 calibration, 30 development and 60 blind test artifacts, grouped by
source case. ContextSidecar artifacts are excluded by user direction.

### Human truth

Obtain two independent blinded labels per test item using observable binary or
ordinal criteria, then adjudicate disagreements. Report raw agreement,
Krippendorff alpha or weighted kappa as appropriate, criterion prevalence and
the adjudicated label. A criterion with inadequate human agreement is revised
or reported as ambiguous; it is not used to validate a judge.

### Automated candidates

1. deterministic executable/schema/business-rule scorers where applicable;
2. one pinned pointwise rubric judge;
3. the same judge with a small calibration mapping over rubric dimensions;
4. pairwise judge with randomized/swapped order on contrast pairs;
5. multi-judge/meta-judge only if candidates 2–4 fail the gate and a second
   family adds independent signal on calibration data.

### Perturbations

Blind model/source identity; randomize candidate order; swap pairwise order;
paraphrase the rubric without changing criteria; add irrelevant formatting;
create length-matched and verbosity-expanded controls; repeat each judge call
three times. Include negative-control transformations where the correct label
must change so a scorer cannot pass by invariance alone.

### Metrics and gate

Report criterion-level accuracy/F1, weighted kappa/ICC as appropriate,
position consistency, repetition stability, false-pass rate, Brier score/ECE,
risk-coverage curve, bootstrap 95% confidence intervals, calls/tokens/cost and
latency. Preserve per-item disagreement rather than only means.

Promote the simplest automated policy only if, on the blind test set:

- deterministic criteria retain 100% seeded-fault detection;
- every criterion used for promotion has human agreement at least 0.70;
- judge macro F1 is at least 0.80 with lower 95% bound at least 0.72;
- false-pass rate on prohibited/unsupported behavior is at most 2%, with no
  missed critical seeded fault;
- position consistency and repetition stability are each at least 0.95;
- selective review at 80% coverage has error no worse than 5%; and
- calibration/panel complexity is retained only when its paired improvement
  exceeds uncertainty and its incremental cost is reported.

If no judge meets the gate, ProofGrid keeps deterministic scoring plus human
review; it does not fabricate an automatic winner.

## PG1 — structured-output method comparison

Run only after PG0 provides intervals and review rules.

### Cases and candidates

Stratify at least 200 JSONSchemaBench schemas by objects/arrays, enums/unions,
references, recursion, numeric/string constraints and unsupported features.
Add 60 application schemas with exact semantic targets, including ambiguous
and missing-evidence cases. Compare under the same model/revision:

1. prompt-only control;
2. provider-native JSON Schema;
3. one pinned local/server grammar engine if a compatible runtime exists;
4. validate-and-retry with a fixed maximum;
5. bounded repair only on predeclared syntax transformations.

### Metrics and gate

Report schema compilation/coverage, valid-first-attempt, semantic exact and
field F1, unsupported-schema refusal, repair semantic corruption, attempts,
time-to-first-token, p95 latency, tokens, cost, RAM/VRAM and repeated-run
variance. A method is non-dominated only if it improves semantic correctness
or a distinct schema/latency/cost region without introducing a critical wrong
value. Syntax validity alone cannot promote it.

## PG2 — metamorphic cross-project suite

Run after two project owners provide reviewed relations. Each relation records
source case, transform, expected invariant/change, applicable project/profile,
negative control and review owner. Start with order/format/paraphrase and
irrelevant-context relations; do not generate arbitrary transformations and
treat them as truth. Promote a relation only after it catches a seeded defect
and has below 5% false alarms on reviewed controls.

## PG3 — framework adapter checks

- Inspect adapter activates only for executable/agent/sandbox tasks.
- JSONSchemaBench adapter activates in PG1.
- lm-evaluation-harness activates only for a named public capability benchmark.
- Promptfoo/DeepEval are not integrated unless one focused component beats the
  retained AutoEvals/ProofGrid seam under the same contract.

Each adapter first proves one success, one relevant failure, versioned raw
artifacts and unchanged review/export/gate behavior.

## Resource and safety envelope

- PG0 offline scoring/human-label import must run on the current CPU host.
- Paid judge calls require a precomputed maximum call/token/USD budget; stop at
  the cap without silently reducing repeats or test cases.
- Local grammar candidates report CPU/GPU and model/server revision separately.
- Untrusted agent/code workloads require an Inspect-compatible sandbox before
  execution.
- No API key, full private context or reviewer identity beyond the declared
  pseudonym is stored in exported evidence.

## Stop rules

- Stop at the first simple policy meeting every PG0 gate.
- Stop a judge/panel that misses a critical seeded fault or whose bias probe
  failure exceeds the pre-registered limit.
- Stop structured-output integration if its shared schema subset cannot pass
  one supported and one unsupported smoke case before runner/store changes.
- Stop a comparison when candidate configuration, truth labels, costs or raw
  results are incomplete; mark it `UNVERIFIED` rather than filling nulls.
- Do not tune on the blind test set or promote a mean whose paired interval is
  consistent with material regression.

## Exact first authorized experiment

After portfolio checkpoint approval, execute **PG0 only**, beginning with the
120-artifact manifest and human-label protocol. Do not call a judge until the
blind rubric and split are frozen. PG1–PG3 remain blocked until PG0 closes.
