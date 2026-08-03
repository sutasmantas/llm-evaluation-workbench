# ProofGrid project start record

Date: 2026-08-01

## 1. Restart boundary

- repository: `portfolio_demos/proofgrid`
- baseline branch and commit: upstream `main` at `b0e1055892bea1305a10f8d42fdc47ff1b41ffa4`
- implementation branch: `agent/proofgrid-depth`
- assigned isolated worktree: `portfolio_demos/worktrees/proofgrid_depth`
- owner/session: current Codex portfolio depth session
- repositories/worktrees that are read-only: every other directory under `portfolio_demos`, especially `context_sidecar` and `worktrees/context_sidecar_c0`
- exact next action: commit this passed start gate, then implement the frozen deterministic experiment without changing the structural layout

Never share this worktree or switch branches inside it.

## 2. Client outcome and non-duplication

- one client-purchased outcome this project proves: turn a frozen set of LLM extraction/classification cases into a repeatable comparison, failure-review queue, and CI promotion decision
- existing portfolio evidence closest to it: Atlas has RAG evaluation artifacts; Relay has governed execution and failure handling; LedgerLens has field correction
- mechanism or deliverable that is genuinely new: a provider-neutral, reusable evaluation runner with versioned prompt/provider runs, schema validation, per-case cost/latency/retry evidence, correction records, and a machine-readable regression gate
- why this is better coverage than deepening an existing project: the runner can test many client AI systems, whereas another Atlas technique would remain RAG-specific and duplicate strong existing evidence

## 3. GitHub foundation comparison

These private working projects are selected on technical fit. License was not researched, filtered, compared, or ranked.

| Candidate | Repository | Activity/version checked | Central behavior reusable for this slice | Adaptation cost/risk | Decision |
| --- | --- | --- | --- | --- | --- |
| Promptfoo | `https://github.com/promptfoo/promptfoo` | `82ca3c24ec445cf1734face46042c187b659b954`, checked 2026-08-01 | mature CLI runner, provider matrix, assertions, exports, and CI gates | roughly 700 MB repository and a broad TypeScript product; portfolio work would be obscured by upstream machinery | reject for this bounded slice |
| DeepEval | `https://github.com/confident-ai/deepeval` | `0abedb84c7db59873125e3c8e66199fa874c4878`, checked 2026-08-01 | pytest-like cases, JSON correctness, datasets, and model-judge metrics | larger judge/platform surface and credential-oriented defaults than the deterministic first experiment needs | reject for this bounded slice |
| AutoEvals | `https://github.com/braintrustdata/autoevals` | `b0e1055892bea1305a10f8d42fdc47ff1b41ffa4`, checked 2026-08-01 | uniform `Scorer`/`Score` contract plus `ValidJSON`, `JSONDiff`, `ExactMatch`, and optional OpenAI-compatible judge clients | runner, persistence, API, review queue, and UI must be added; this is useful portfolio-owned work rather than duplicate framework surface | select |

Selected foundation:

- repository URL: `https://github.com/braintrustdata/autoevals.git`
- pinned tag/commit: `b0e1055892bea1305a10f8d42fdc47ff1b41ffa4`
- exact code/package/contracts reused: the Python `Score` and `Scorer` contract; `ValidJSON` for JSON/schema validity; `JSONDiff` for structured similarity; `ExactMatch` for deterministic comparisons; the OpenAI-compatible client boundary remains optional rather than required for the no-key proof
- upstream history/identity preservation: the local engineering repository keeps the shallow upstream history and the AutoEvals source as `upstream`; the user-owned public repository is a publication snapshot because the intentionally shallow source cannot provide a complete standalone pack
- why this is faster/safer than starting blank: proven scorer normalization and schema/diff behavior are reused while the new code concentrates on the missing commercial workflow—batch execution, versioned records, promotion gates, review, and reporting

## 4. Distinct visual direction

The comparison uses rendered working-state screenshots, not logos or marketing covers.

| Existing project | Screenshot inspected | Spatial model | Navigation | Palette family | Typography character | Geometry/surface model | Dominant interaction | ProofGrid differences |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Atlas | `worktrees/atlas_main/docs/screenshots/atlas-answer.png` | query rail + answer canvas + evidence pane | compact header and query rail | warm neutral + violet | editorial serif/sans | soft bordered reading surfaces | ask, cite, inspect evidence | run-by-case grid, no answer canvas or evidence pane; cold white/cobalt/raspberry; square ruled cells |
| Relay | `support_automation/docs/screenshots/relay-workflow.png` | workflow graph + approval inspector + timeline | dark top product tabs | deep teal | operations sans/mono | nodes on dotted canvas | traverse and approve a workflow | fixed comparison matrix with no graph, inspector, or timeline; light proof-sheet density |
| LedgerLens | `document_extraction/docs/screenshots/document-review.png` | queue + page canvas + field form | document queue | paper neutral + amber | document-review sans/serif | page sheet and form cards | correct fields against a document | many-case cross-run sweep; no document viewer, sidebar queue, or form column |
| SignalRoom | `retention_decisioning/docs/screenshots/signalroom-decision-room.png` | dashboard curve + controls + account table | permanent left nav | dark navy + lime | analytical sans/mono | dark dashboard panels | tune a policy threshold | no dashboard cards, curve, or side navigation; row/column proofing and binary promotion rail |
| Website Assistant | rendered local storefront/chat state reviewed 2026-08-01 | oversized editorial storefront with chat launcher | retail header | warm merchandise neutrals | display editorial | large image/content blocks | open chat and request handoff | dense technical matrix, no launcher, storefront, hero, or conversation thread |
| Printline | `generative_workflow/docs/screenshots/printline-workstation-1440.png` | dark artboard + control deck + filmstrip | workstation header | charcoal + acid yellow/purple | industrial mono/sans | artboard and control panels | edit recipe and render frame | white proof sheet; no central artboard, right control deck, or filmstrip |
| Gauge | `vision_inspection/docs/screenshots/gauge-station-1440.png` | infeed rail + optical stage + signal tower | station rail | cream/black/yellow/red | heavy industrial | circular inspection viewport | inspect one part and disposition | rectangular multi-case grid; no camera viewport, signal tower, or floor-console controls |
| LeadDock | `lead_dock/docs/leaddock-1440.png` | arrival tape + appointment ledger + receipt tape | queue strip | lavender/aubergine/coral | condensed dispatch sans/mono | ledger rows and receipt band | qualify and book one lead | simultaneous run comparison with selected-cell evidence and promotion rule; no appointment chronology or arrival tape |

- comparison projects/screenshots reviewed: Atlas, Relay, LedgerLens, SignalRoom, Website Assistant, Printline, Gauge, and LeadDock
- product/audience metaphor: a QA proof sheet where an AI engineer sweeps the same cases across candidate runs and promotes only a measured winner
- layout structure: compact command strip; sticky case axis; three equal run columns; selected-cell evidence band; full-width bottom promotion rail
- palette: cold paper white and blue-gray rules, cobalt for structured output, raspberry for failed checks, cyan for reviewed/repair evidence, near-black text
- typography character: wide neo-grotesk headings with compact tabular/monospace evidence labels; no editorial serif or industrial stencil voice
- primary interaction pattern: scan horizontally across one frozen case, select a result cell, review failure evidence in the bottom tray, then accept/correct and re-evaluate the promotion gate
- explicit patterns avoided because another project already uses them: no permanent sidebar, KPI-card hero, workflow graph, three-column inspector, document canvas, chat thread, artboard/control deck, circular inspection viewport, or chronological booking ledger
- 1440 px first-viewport evidence: `docs/identity/proofgrid-1440.png`
- 1024 px responsive evidence: `docs/identity/proofgrid-1024.png`
- 390 px responsive evidence: `docs/identity/proofgrid-390.png`
- closest visual neighbor and why this is not a reskin: Relay also exposes governed failures, but Relay is a node graph with a right inspector and event timeline; ProofGrid is a light row/column comparison instrument with a bottom evidence tray and promotion rail

Rendered identity gate: `PASS` on 2026-08-01.

- 1440 px: the whole working state fits in the first viewport; the comparison
  matrix, selected-cell evidence tray, and release gate establish a spatial
  model absent from the current portfolio.
- 1024 px: the three candidate columns, sticky case axis, evidence tray, and
  release gate remain legible without changing the interaction hierarchy.
- 390 px: the case axis remains pinned, candidate columns become an intentional
  horizontal comparison surface, and the evidence tray stacks vertically.
- distinction result: spatial model and dominant interaction differ from every
  inspected project; navigation, palette, typography, geometry, and density
  differ from the closest neighbor, Relay. Gate `PASS`.

## 5. Minimum referenceable evidence contract

| Gate | Observable acceptance evidence | Status |
| --- | --- | --- |
| Central similarity | frozen extraction/classification set executes against baseline, structured, and repair candidates through reused AutoEvals scorers | PASS |
| Working vertical slice | import -> run -> compare -> review correction -> gate -> export works through API/CLI and UI | PASS |
| No-key deterministic proof | bundled adapter creates stable outputs and costs without credentials | PASS |
| Invalid input and abuse behavior | malformed CSV/JSONL, oversized batches, invalid schemas, and unsupported formats fail explicitly | PASS |
| Provider/tool failure and retry/refusal/handoff | OpenAI-compatible transient failure is classified, bounded, and recorded; permanent failure enters review rather than receiving fabricated output | PASS |
| Focused mechanism tests | scorer reuse, imports, version hashes, schema/diff checks, retries, review persistence, and promotion thresholds are covered | PASS |
| Clean-checkout quickstart | detached `proofgrid_verify` at `54b6870` completed locked install, 19 tests, and deterministic winner run | PASS |
| Cover-letter claim ledger | `docs/CLAIM_LEDGER.md` ties each allowed claim to a command/artifact | PASS |
| Honest unsupported-claim boundary | no provider-superiority, production-scale, judge-ground-truth, client outcome, or hosted reliability claim | PASS |

Only all `PASS` closes this slice. Stop before decorative polish, extra providers, or broad production hardening.

## 6. Verification and handback

- static/type/lint command: Black check, isort check, Flake8, compileall, and `git diff --check`
- focused tests: `python -m pytest -q py/autoevals/test_json.py py/autoevals/test_serializable_data_class.py py/proofgrid`
- integration/demo command: `proofgrid run --require-winner --output .proofgrid/run.json`; live API/browser flow at 1440/1024/390
- build/package command: `python -m build` and `python -m twine check dist/*`
- branch and final commit: completed `agent/proofgrid-depth` at `df727c1`; merged to local `main` at `5535a4a`; final integration checkpoint is the commit containing this update
- clean state: detached clean verification passed; assigned worktree must be clean after the closure commit
- known boundaries: deterministic fixtures are not provider rankings; the selected foundation's optional model judges require configured credentials; local SQLite/single-process execution is not a production-scale claim
- exact next portfolio action: after this slice closes, rank the shared delivery/reliability kit against the updated checkpoint
