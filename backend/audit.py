"""Append-only audit trail for PydanticAI agent/tool activity (Problem 12).

Format: JSON Lines (one JSON object per line) in output/audit_trail.json.
JSON Lines is used specifically because it is naturally append-only - each
new record is a single `open(path, 'a')` write, so there is never a
read-modify-write cycle that could truncate or corrupt prior entries, and a
partially-written last line does not affect any earlier record.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

AUDIT_PATH = Path(__file__).parent.parent / "output" / "audit_trail.json"

# Keys whose values must never be written to the audit trail, regardless of
# which tool/record they came from.
_SENSITIVE_KEYS = {
    "password", "password_hash", "api_key", "apikey", "portkey_api_key",
    "authorization", "token", "secret", "credential",
}

_MAX_FIELD_LENGTH = 200  # keep args/results short, per the rubric


def _sanitize(value):
    """Recursively redact sensitive keys and truncate long values."""
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if k.lower() in _SENSITIVE_KEYS else _sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(v) for v in value[:5]]  # cap list length too
    if isinstance(value, str):
        return value if len(value) <= _MAX_FIELD_LENGTH else value[:_MAX_FIELD_LENGTH] + "...[truncated]"
    return value


def append_audit_record(
    tool_name: str,
    args: dict | str | None,
    result: str | None,
    stop_reason: str,
) -> None:
    """Append one sanitized, short audit record. Never overwrites existing content.

    Safe against a missing output/ directory and against the file not
    existing yet - creates both as needed without touching any prior data.
    """
    try:
        record = {
            "time": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "args": _sanitize(args),
            "result": _sanitize(result),
            "stop_reason": stop_reason,
        }
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:
        # Audit logging must never break the chat request itself.
        logger.exception("Failed to append audit record (non-fatal)")


def record_agent_run(message: str, result, user_id, error: Exception | None = None) -> None:
    """Extract real tool-call activity from a completed PydanticAI run and
    append one audit record per tool call, plus one summary record for the
    overall turn. Never raises - audit failures must not break chat.
    """
    try:
        if error is not None:
            append_audit_record(
                tool_name="agent.run",
                args={"message": message[:_MAX_FIELD_LENGTH], "user_id": user_id},
                result=str(error),
                stop_reason="error",
            )
            return

        # Pair ToolCallPart / ToolReturnPart by tool_call_id across this run's
        # new messages so each record reflects a real tool invocation.
        calls = {}
        returns = {}
        for msg in result.new_messages():
            for part in getattr(msg, "parts", []):
                kind = getattr(part, "part_kind", None)
                if kind == "tool-call":
                    calls[part.tool_call_id] = part
                elif kind == "tool-return":
                    returns[part.tool_call_id] = part

        for call_id, call_part in calls.items():
            return_part = returns.get(call_id)
            append_audit_record(
                tool_name=call_part.tool_name,
                args=call_part.args,
                result=getattr(return_part, "content", None) if return_part else None,
                stop_reason="tool_call",
            )

        append_audit_record(
            tool_name="agent.run",
            args={"message": message[:_MAX_FIELD_LENGTH], "user_id": user_id},
            result=str(result.output)[:_MAX_FIELD_LENGTH],
            stop_reason="completed",
        )
    except Exception:
        logger.exception("Failed to record agent run audit activity (non-fatal)")
