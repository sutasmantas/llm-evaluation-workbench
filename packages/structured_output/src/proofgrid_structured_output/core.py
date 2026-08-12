from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from typing import Any, Literal

import jsonschema
from proofgrid_provider import ChatRequest, Message, Provider

FailureStage = Literal["extract", "parse", "validate"]
FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class SchemaError(ValueError):
    """The response did not become schema-conformant."""

    def __init__(self, stage: FailureStage, detail: str) -> None:
        self.stage = stage
        self.detail = detail
        super().__init__(f"structured output rejected at {stage}: {detail}")


@dataclass(frozen=True)
class Attempt:
    raw: str
    stage: str
    error: str | None = None


@dataclass
class Result:
    value: Any | None
    attempts: list[Attempt] = field(default_factory=list)
    ok: bool = False

    @property
    def tries(self) -> int:
        return len(self.attempts)


def extract_json(text: str) -> str:
    if not text or not text.strip():
        raise ValueError("empty response")
    fenced = FENCE.search(text)
    if fenced and fenced.group(1).strip():
        return fenced.group(1).strip()

    stripped = text.strip()
    starts = [index for index in (stripped.find("{"), stripped.find("[")) if index >= 0]
    if not starts:
        raise ValueError("no JSON object or array found in response")
    start = min(starts)
    stack: list[str] = []
    in_string = False
    escaped = False
    pairs = {"}": "{", "]": "["}
    for index in range(start, len(stripped)):
        character = stripped[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "{[":
            stack.append(character)
        elif character in "}]":
            if not stack or stack[-1] != pairs[character]:
                return stripped[start:]
            stack.pop()
            if not stack:
                return stripped[start : index + 1]
    # Extraction found a candidate. Leaving it for json.loads preserves the
    # parse-stage distinction and the decoder's useful error position.
    return stripped[start:]


def validate(value: Any, schema: dict[str, Any]) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    ]


def coerce(text: str, schema: dict[str, Any]) -> tuple[Any | None, str, str | None]:
    try:
        payload = extract_json(text)
    except ValueError as exc:
        return None, "extract", str(exc)
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        return None, "parse", f"invalid JSON: {exc}"
    errors = validate(value, schema)
    if errors:
        return None, "validate", "; ".join(errors[:6])
    return value, "ok", None


def parse(text: str, schema: dict[str, Any]) -> Any:
    value, stage, error = coerce(text, schema)
    if stage != "ok":
        raise SchemaError(stage, error or "unknown structured-output failure")
    return value


def _with_instruction(request: ChatRequest, instruction: str) -> ChatRequest:
    return replace(
        request,
        messages=(*request.messages, Message("user", instruction)),
        response_format=request.response_format or {"type": "json_object"},
    )


def generate(
    provider: Provider,
    request: ChatRequest,
    schema: dict[str, Any],
    *,
    max_attempts: int = 3,
    timeout: float = 45,
) -> Result:
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")
    schema_text = json.dumps(schema, indent=2, sort_keys=True)
    current = _with_instruction(
        request,
        "Return JSON only, conforming exactly to this schema:\n" + schema_text,
    )
    result = Result(value=None)
    for attempt_number in range(1, max_attempts + 1):
        completion = provider.complete(current, timeout=timeout)
        value, stage, error = coerce(completion.text, schema)
        result.attempts.append(Attempt(completion.text[:400], stage, error))
        if stage == "ok":
            result.value = value
            result.ok = True
            return result
        if attempt_number < max_attempts:
            current = _with_instruction(
                request,
                f"Your previous response was rejected at the {stage} stage: {error}\n\n"
                "Return JSON only, conforming exactly to this schema:\n" + schema_text,
            )
    return result
