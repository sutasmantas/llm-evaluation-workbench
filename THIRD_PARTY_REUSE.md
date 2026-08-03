# Third-party reuse

## Selected foundation

- upstream: `https://github.com/braintrustdata/autoevals.git`
- pinned commit: `b0e1055892bea1305a10f8d42fdc47ff1b41ffa4`
- history: preserved as this repository's shallow baseline and `origin`

ProofGrid directly reuses the Python `Score`/`Scorer` abstraction,
`ValidJSON`, `JSONDiff`, and `ExactMatch`. These are central to every case
result: schema validity, structured similarity, and exact promotion evidence
are not reimplemented local lookalikes.

The external-observation workflow also reuses AutoEvals `Score` as the stored
human-rubric result contract. ProofGrid supplies the application-specific six
dimension rubric and stream-index validation, while normalized score shape and
metadata serialization remain on the selected upstream foundation.

The portfolio-owned code adds the behavior the smaller foundation does not
provide: case imports, frozen version manifests, three-path orchestration,
provider retry normalization, SQLite run/review records, correction-driven
gate recomputation, CLI/API exports, and the ProofGrid comparison interface.

## Compared but not adopted

- Promptfoo at `82ca3c24ec445cf1734face46042c187b659b954` supplies a mature runner,
  provider matrix, assertions, exports, and CI flows. Its much larger product
  surface would obscure the bounded portfolio-owned mechanism.
- DeepEval at `0abedb84c7db59873125e3c8e66199fa874c4878` supplies pytest-like
  evaluation and broad judge metrics. Its judge/platform-oriented surface is
  larger than the deterministic first experiment requires.

The comparison intentionally did not research, filter, compare, or rank
licenses, per the user's standing private-project rule.

## Executable integration notes

Two upstream calling details are protected by ProofGrid tests:

1. `ValidJSON.eval` forwards the base scorer's second positional argument into
   a subclass parameter named `schema`; passing `schema=` by keyword produces
   a duplicate-argument error. ProofGrid passes the frozen schema positionally.
2. `ExactMatch` serializes dictionaries without sorting keys. ProofGrid
   canonicalizes output and expected JSON before invoking it so key order does
   not create a false mismatch.
