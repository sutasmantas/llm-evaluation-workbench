from __future__ import annotations

import json

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from proofgrid.inspect_integration import CONTRACT_VERSION, INSPECT_AI_REVISION, json_schema_contract, observed_json


@task
def proofgrid_inspect_reference(*, contract_mutant: bool = False) -> Task:
    """Run the smallest provider-owned executable-evaluation reference."""

    schema = {
        "type": "object",
        "properties": {"ready": {"const": True}},
        "required": ["ready"],
        "additionalProperties": False,
    }
    return Task(
        dataset=[
            Sample(
                id="provider-reference",
                input="Import one versioned executable observation",
                target=json.dumps(schema, sort_keys=True),
                metadata={
                    "observed": {"ready": not contract_mutant},
                    "split": "heldout",
                    "category": "provider-reference",
                },
            )
        ],
        solver=observed_json(),
        scorer=json_schema_contract(),
        name="proofgrid_inspect_reference",
        version="1",
        metadata={
            "proofgrid_contract": CONTRACT_VERSION,
            "inspect_revision": INSPECT_AI_REVISION,
            "mutation": "ready-false" if contract_mutant else None,
        },
    )
