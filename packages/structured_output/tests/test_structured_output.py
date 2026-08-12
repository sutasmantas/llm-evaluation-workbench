from __future__ import annotations

from dataclasses import dataclass

import pytest
from proofgrid_provider import Capabilities, ChatRequest, Completion, Message
from proofgrid_structured_output import SchemaError, coerce, generate, parse

SCHEMA = {
    "type": "object",
    "required": ["summary", "severity", "tags"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "count": {"type": "integer"},
    },
}
GOOD = '{"summary": "disk filled", "severity": "high", "tags": ["ops"]}'

CASES: list[tuple[str, str, str | None]] = [
    ("clean", GOOD, None),
    ("fenced", f"```json\n{GOOD}\n```", None),
    ("fenced-no-lang", f"```\n{GOOD}\n```", None),
    ("prose-then-json", f"Sure! Here is the result:\n{GOOD}", None),
    ("json-then-prose", f"{GOOD}\nLet me know if you need changes.", None),
    ("empty", "", "extract"),
    ("whitespace", "   \n  ", "extract"),
    ("no-json", "I cannot help with that request.", "extract"),
    ("truncated", '{"summary": "disk filled", "severity":', "parse"),
    ("trailing-comma", '{"summary": "x", "severity": "high", "tags": ["a"],}', "parse"),
    ("single-quotes", "{'summary': 'x', 'severity': 'high', 'tags': ['a']}", "parse"),
    ("missing-required", '{"summary": "x", "severity": "high"}', "validate"),
    ("bad-enum", '{"summary": "x", "severity": "critical", "tags": ["a"]}', "validate"),
    ("wrong-type", '{"summary": 42, "severity": "high", "tags": ["a"]}', "validate"),
    ("empty-array", '{"summary": "x", "severity": "high", "tags": []}', "validate"),
    ("wrong-item-type", '{"summary": "x", "severity": "high", "tags": [1, 2]}', "validate"),
    ("extra-property", '{"summary": "x", "severity": "high", "tags": ["a"], "oops": 1}', "validate"),
    ("bool-as-integer", '{"summary": "x", "severity": "high", "tags": ["a"], "count": true}', "validate"),
    ("array-at-root", '[{"summary": "x"}]', "validate"),
    ("brace-in-string", '{"summary": "use {curly} braces", "severity": "low", "tags": ["a"]}', None),
    ("escaped-quote", '{"summary": "say \\"hi\\"", "severity": "low", "tags": ["a"]}', None),
    (
        "nested-object-prose",
        'Result below.\n{"summary": "x", "severity": "low", "tags": ["a"], "count": 3}\nDone.',
        None,
    ),
]


@pytest.mark.parametrize(("_name", "response", "expected_stage"), CASES)
def test_construction_known_response_shapes(_name: str, response: str, expected_stage: str | None) -> None:
    value, stage, _error = coerce(response, SCHEMA)
    if expected_stage is None:
        assert stage == "ok"
        assert value is not None
    else:
        assert stage == expected_stage
        assert value is None


RELAY_SCHEMA = {
    "type": "object",
    "required": [
        "intent",
        "priority",
        "sentiment",
        "route",
        "confidence",
        "risk_reason",
        "draft",
    ],
    "additionalProperties": False,
    "properties": {
        "intent": {"type": "string"},
        "priority": {"type": "string"},
        "sentiment": {"type": "string"},
        "route": {"type": "string"},
        "confidence": {"type": "number"},
        "risk_reason": {"type": "string"},
        "draft": {"type": "string"},
    },
}
RELAY_GOOD = (
    '{"intent":"Failed renewal","priority":"Urgent","sentiment":"Concerned",'
    '"route":"Billing Ops","confidence":0.96,"risk_reason":"approval required",'
    '"draft":"We are reviewing the renewal."}'
)


@pytest.mark.parametrize("response", [RELAY_GOOD, f"```json\n{RELAY_GOOD}\n```", RELAY_GOOD + "\nDone."])
def test_relay_shaped_clean_twins(response: str) -> None:
    assert parse(response, RELAY_SCHEMA)["confidence"] == 0.96


@pytest.mark.parametrize(
    ("response", "detail"),
    [
        (RELAY_GOOD.replace('"draft":"We are reviewing the renewal."', '"extra":true'), "draft"),
        (RELAY_GOOD[:-1] + ',"extra":true}', "extra"),
        (RELAY_GOOD.replace('"confidence":0.96', '"confidence":"high"'), "confidence"),
    ],
)
def test_relay_shaped_defects_are_refused(response: str, detail: str) -> None:
    with pytest.raises(SchemaError, match=detail) as caught:
        parse(response, RELAY_SCHEMA)
    assert caught.value.stage == "validate"


@dataclass
class ScriptedProvider:
    responses: list[str]
    capabilities = Capabilities("scripted", False, False, True, True, False)

    def __post_init__(self) -> None:
        self.requests: list[ChatRequest] = []

    def complete(self, request: ChatRequest, *, timeout: float = 45) -> Completion:
        del timeout
        self.requests.append(request)
        return Completion(self.responses.pop(0), "scripted", request.model, 0.0)


def test_generate_repairs_with_exact_stage_and_never_returns_partial() -> None:
    provider = ScriptedProvider(['{"summary": "x"}', GOOD])
    result = generate(
        provider,
        ChatRequest((Message("user", "Classify the incident."),), "test-model"),
        SCHEMA,
        max_attempts=2,
    )
    assert result.ok
    assert result.tries == 2
    assert result.attempts[0].stage == "validate"
    repair_message = provider.requests[1].messages[-1].content
    assert "severity" in repair_message
    assert "is a required property" in repair_message

    exhausted = generate(
        ScriptedProvider(["not json", "still not json"]),
        ChatRequest((Message("user", "Classify the incident."),), "test-model"),
        SCHEMA,
        max_attempts=2,
    )
    assert not exhausted.ok
    assert exhausted.value is None
    assert [attempt.stage for attempt in exhausted.attempts] == ["extract", "extract"]
