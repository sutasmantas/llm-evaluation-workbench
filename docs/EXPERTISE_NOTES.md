# ProofGrid expertise notes

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
