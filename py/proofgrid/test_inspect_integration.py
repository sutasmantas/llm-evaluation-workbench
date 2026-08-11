from __future__ import annotations

import json

import pytest
from inspect_ai import Task, eval
from inspect_ai.dataset import Sample

from .inspect_integration import (
    CONTRACT_VERSION,
    INSPECT_AI_REVISION,
    import_inspect_log,
    json_schema_contract,
    observed_json,
)
from .store import RunStore


def reference_task(observed: dict[str, object], *, metadata: dict[str, str] | None = None) -> Task:
    schema = {
        "type": "object",
        "properties": {"ok": {"const": True}},
        "required": ["ok"],
        "additionalProperties": False,
    }
    return Task(
        dataset=[
            Sample(
                id="reference",
                input="precomputed provider observation",
                target=json.dumps(schema),
                metadata={"observed": observed, "split": "heldout", "category": "reference"},
            )
        ],
        solver=observed_json(),
        scorer=json_schema_contract(),
        name="proofgrid_reference",
        version="1",
        metadata=(
            metadata
            if metadata is not None
            else {"proofgrid_contract": CONTRACT_VERSION, "inspect_revision": INSPECT_AI_REVISION}
        ),
    )


def execute(task: Task, log_dir: str):
    return eval(task, model="mockllm/model", log_dir=log_dir, log_format="json", display="none")[0]


def test_reference_task_imports_and_persists_a_passing_contract(tmp_path):
    result = import_inspect_log(execute(reference_task({"ok": True}), str(tmp_path / "logs")))

    assert result["kind"] == "inspect_executable_evaluation"
    assert result["decision"]["winner"] == "proofgrid_reference"
    assert result["candidates"][0]["summary"]["pass_rate"] == 1
    assert result["source"]["log_name"].endswith(".json")
    assert len(result["source"]["log_sha256"]) == 64
    assert "test_reference_task" not in result["source"]["log_name"]
    store = RunStore(tmp_path / "runs.sqlite3")
    store.save_run(result)
    assert store.get_run(result["run_id"])["suite_hash"] == result["suite_hash"]


def test_reference_task_rejects_a_contract_mutation(tmp_path):
    result = import_inspect_log(execute(reference_task({"ok": False}), str(tmp_path / "logs")))

    row = result["candidates"][0]["rows"][0]
    assert result["decision"]["winner"] is None
    assert row["failure_class"] == "contract_mismatch"
    assert row["passed"] is False


def test_import_refuses_missing_contract_metadata(tmp_path):
    log = execute(reference_task({"ok": True}, metadata={}), str(tmp_path / "logs"))

    with pytest.raises(ValueError, match="proofgrid_contract"):
        import_inspect_log(log)


def test_import_refuses_an_unversioned_task(tmp_path):
    log = execute(reference_task({"ok": True}), str(tmp_path / "logs"))
    log.eval.task_version = None

    with pytest.raises(ValueError, match="task_version"):
        import_inspect_log(log)


def test_import_refuses_a_different_inspect_build(tmp_path):
    log = execute(reference_task({"ok": True}), str(tmp_path / "logs"))
    log.eval.packages["inspect_ai"] = "unexpected"

    with pytest.raises(ValueError, match="Inspect log must use inspect_ai"):
        import_inspect_log(log)


def test_import_refuses_duplicate_sample_ids(tmp_path):
    log = execute(reference_task({"ok": True}), str(tmp_path / "logs"))
    log.samples.append(log.samples[0].model_copy(deep=True))

    with pytest.raises(ValueError, match="duplicate Inspect sample id"):
        import_inspect_log(log)


def test_import_refuses_a_missing_required_scorer(tmp_path):
    log = execute(reference_task({"ok": True}), str(tmp_path / "logs"))
    log.samples[0].scores = {}

    with pytest.raises(ValueError, match="missing scorer"):
        import_inspect_log(log)
