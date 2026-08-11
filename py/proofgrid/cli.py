from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .observations import DEFAULT_ANSWER_PROMOTION, import_observation_bundles, load_observation_bundle
from .providers import adapter_from_environment
from .runner import adapters_for_candidates, execute_suite, load_candidates, load_cases
from .store import RunStore, result_to_csv


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = ROOT / "evals" / "proofgrid"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="proofgrid", description="Run and inspect bounded LLM reliability suites")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="execute a case set")
    run.add_argument("--cases", type=Path, default=DEFAULT_SUITE / "cases.jsonl")
    run.add_argument("--candidates", type=Path, default=DEFAULT_SUITE / "candidates.json")
    run.add_argument("--schema", type=Path, default=DEFAULT_SUITE / "schema.json")
    run.add_argument("--promotion", type=Path, default=DEFAULT_SUITE / "promotion.json")
    run.add_argument("--db", type=Path, default=Path(".proofgrid/runs.sqlite3"))
    run.add_argument("--output", type=Path)
    run.add_argument("--require-winner", action="store_true")
    run.add_argument("--judge", action="store_true", help="enable the optional OpenAI-compatible rubric judge")

    observations = subparsers.add_parser(
        "import-observations", help="import precomputed application-path observations"
    )
    observations.add_argument("--bundle", action="append", type=Path, required=True)
    observations.add_argument("--pricing", type=Path)
    observations.add_argument("--promotion", type=Path)
    observations.add_argument("--db", type=Path, default=Path(".proofgrid/runs.sqlite3"))
    observations.add_argument("--output", type=Path)

    inspect_import = subparsers.add_parser("import-inspect", help="import a pinned Inspect executable-evaluation log")
    inspect_import.add_argument("--log", type=Path, required=True)
    inspect_import.add_argument("--scorer", default="json_schema_contract")
    inspect_import.add_argument("--minimum-score", type=float, default=1.0)
    inspect_import.add_argument("--db", type=Path, default=Path(".proofgrid/runs.sqlite3"))
    inspect_import.add_argument("--output", type=Path)
    inspect_import.add_argument("--require-pass", action="store_true")

    review_answer = subparsers.add_parser("review-answer", help="resolve one imported answer review")
    review_answer.add_argument("--db", type=Path, default=Path(".proofgrid/runs.sqlite3"))
    review_answer.add_argument("--review-id", required=True)
    review_answer.add_argument("--review", type=Path, required=True)

    reviews = subparsers.add_parser("reviews", help="list persisted review records")
    reviews.add_argument("--db", type=Path, default=Path(".proofgrid/runs.sqlite3"))
    reviews.add_argument("--run-id")
    reviews.add_argument("--status", choices=("open", "resolved"))

    export = subparsers.add_parser("export", help="export the latest run")
    export.add_argument("--db", type=Path, default=Path(".proofgrid/runs.sqlite3"))
    export.add_argument("--format", choices=("json", "csv"), default="json")
    export.add_argument("--output", type=Path, required=True)

    serve = subparsers.add_parser("serve", help="serve the local API and workbench")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--db", type=Path, default=Path(".proofgrid/runs.sqlite3"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "run":
        candidates = load_candidates(args.candidates)
        result = execute_suite(
            load_cases(args.cases),
            candidates,
            _json(args.schema),
            _json(args.promotion),
            adapters=adapters_for_candidates(candidates),
            judge=adapter_from_environment("PROOFGRID_JUDGE", "judge") if args.judge else None,
        )
        RunStore(args.db).save_run(result)
        serialized = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n", encoding="utf-8")
        print(json.dumps({"run_id": result["run_id"], "decision": result["decision"]}, indent=2))
        if args.require_winner and result["decision"]["winner"] is None:
            return 2
        return 0
    if args.command == "import-observations":
        result = import_observation_bundles(
            [load_observation_bundle(path) for path in args.bundle],
            pricing=_json(args.pricing) if args.pricing else None,
            promotion=_json(args.promotion) if args.promotion else DEFAULT_ANSWER_PROMOTION,
        )
        RunStore(args.db).save_run(result)
        serialized = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n", encoding="utf-8")
        print(json.dumps({"run_id": result["run_id"], "decision": result["decision"]}, indent=2))
        return 0
    if args.command == "import-inspect":
        try:
            from .inspect_integration import import_inspect_log
        except ImportError as exc:
            raise SystemExit("install ProofGrid with the inspect extra to import Inspect logs") from exc
        result = import_inspect_log(
            args.log,
            scorer_name=args.scorer,
            minimum_score=args.minimum_score,
        )
        RunStore(args.db).save_run(result)
        serialized = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n", encoding="utf-8")
        print(json.dumps({"run_id": result["run_id"], "decision": result["decision"]}, indent=2))
        if args.require_pass and result["decision"]["winner"] is None:
            return 2
        return 0
    if args.command == "review-answer":
        review = _json(args.review)
        resolved = RunStore(args.db).resolve_answer_review(
            args.review_id,
            reviewer=review.get("reviewer", ""),
            first_useful_delta_index=review.get("first_useful_delta_index"),
            scores=review.get("scores") or {},
            note=review.get("note", ""),
        )
        print(json.dumps(resolved, ensure_ascii=False, indent=2))
        return 0
    if args.command == "reviews":
        print(
            json.dumps(
                RunStore(args.db).list_reviews(run_id=args.run_id, status=args.status),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "export":
        result = RunStore(args.db).latest_run()
        if result is None:
            raise SystemExit("no evaluation run exists")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.format == "csv":
            args.output.write_text(result_to_csv(result), encoding="utf-8", newline="")
        else:
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    if args.command == "serve":
        os.environ["PROOFGRID_DB_PATH"] = str(args.db.resolve())
        import uvicorn

        uvicorn.run("proofgrid.api:create_app", factory=True, host=args.host, port=args.port)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
