# ProofGrid

ProofGrid is a local-first reliability workbench for comparing LLM prompts,
models, schemas, and repair strategies against the same versioned cases. It
tracks output quality, latency, token use, cost, retries, validation failures,
and human corrections in one inspectable run.

![ProofGrid comparison workspace](docs/screenshots/proofgrid-1440.png)

[Open the live evaluation workspace](https://sutasmantas.github.io/llm-evaluation-workbench/)

## What it handles

- JSONL and CSV case imports with frozen train/held-out splits;
- versioned prompt, schema, provider, pricing, and rubric configuration;
- exact, JSON-schema, diff, and application-specific scorers;
- baseline-versus-candidate comparisons with promotion thresholds;
- retry, parse, validation, latency, token, and cost evidence;
- persistent review corrections and recomputed promotion decisions;
- JSON and CSV exports for client reports or CI gates;
- imported observations from an application's real provider path.

The included run compares baseline, schema-constrained, and bounded-repair
paths over 18 extraction and classification cases. Six cases are held out, and
the promotion thresholds are fixed before execution.

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\proofgrid.exe run --require-winner --output .proofgrid\run.json
.\.venv\Scripts\proofgrid.exe serve --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765` to compare candidates, inspect case-level
differences, resolve review items, and export the run.

## Connect a model or application

For an OpenAI-compatible candidate, set:

```text
PROOFGRID_PROVIDER_BASE_URL=https://your-provider.example/v1
PROOFGRID_PROVIDER_API_KEY=...
PROOFGRID_PROVIDER_MODEL=...
```

Optional `*_INPUT_COST_PER_MILLION` and `*_OUTPUT_COST_PER_MILLION` values add
cost accounting. A separate judge can be configured with the corresponding
`PROOFGRID_JUDGE_*` variables.

Existing applications can import their own observations without replacing
their provider adapter:

```powershell
.\.venv\Scripts\proofgrid.exe import-observations `
  --bundle .proofgrid\candidate-a.json `
  --bundle .proofgrid\candidate-b.json `
  --db .proofgrid\runs.sqlite3
.\.venv\Scripts\proofgrid.exe reviews --db .proofgrid\runs.sqlite3 --status open
```

The observation contract preserves configuration versions, pricing, rubric,
first-useful timing, review state, and case-level comparison evidence.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q py\autoevals\test_json.py py\autoevals\test_serializable_data_class.py py\proofgrid
.\.venv\Scripts\python.exe -m black --check py\proofgrid
.\.venv\Scripts\python.exe -m isort --check-only py\proofgrid
.\.venv\Scripts\python.exe -m flake8 py\proofgrid
.\.venv\Scripts\proofgrid.exe run --require-winner
.\.venv\Scripts\proofgrid.exe export --format csv --output .proofgrid\cases.csv
```

See [the observation integration guide](docs/CONTEXTSIDECAR_OBSERVATION_INTEGRATION.md)
for the versioned bundle and cross-application workflow.
