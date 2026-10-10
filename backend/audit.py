"""Append-only audit trail at output/audit_trail.json.

The file is one JSON array. Each event is appended by reading the array, adding to
it, and atomically replacing the file - earlier runs are never wiped.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from .config import AUDIT_PATH, AUDIT_TEXT_LIMIT, MODEL_NAME
from .models import AuditEvent, AuditEventType, TeamDeps

_lock = threading.Lock()


def _clip(value: Any) -> Any:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(text) <= AUDIT_TEXT_LIMIT:
        return value
    return text[:AUDIT_TEXT_LIMIT] + f"... [truncated {len(text) - AUDIT_TEXT_LIMIT} chars]"


def append_event(event: AuditEvent) -> None:
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        events: list = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size:
            try:
                events = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # Never destroy history: keep the unreadable file and start a new one.
                AUDIT_PATH.replace(AUDIT_PATH.with_suffix(".corrupt.json"))
        events.append(event.model_dump())
        tmp = AUDIT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(events, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, AUDIT_PATH)


def record(deps: TeamDeps | None, event: AuditEventType, detail: dict[str, Any], *,
           step: int | None = None, usage: Any = None, run_id: str | None = None,
           ticket_id: int | None = None) -> None:
    append_event(AuditEvent(
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        run_id=deps.run_id if deps else (run_id or ""),
        ticket_id=deps.ticket_id if deps else ticket_id,
        agent=deps.agent if deps else None,
        depth=deps.depth if deps else 0,
        chain=list(deps.chain) if deps else [],
        step=step,
        event=event,
        model=MODEL_NAME,
        # Only long strings are clipped here; structured values (like the parts lists
        # from record_node, whose contents are already clipped) keep their shape.
        detail={k: _clip(v) if isinstance(v, str) else v for k, v in detail.items()},
        usage=_usage_dict(usage) if usage is not None else None,
    ))


def _usage_dict(usage: Any) -> dict[str, Any]:
    return {
        "requests": getattr(usage, "requests", None),
        "tool_calls": getattr(usage, "tool_calls", None),
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def record_node(deps: TeamDeps, step: int, node: Any, usage: Any) -> None:
    """Turn one agent-graph node into an audit event."""
    if Agent.is_user_prompt_node(node):
        record(deps, "user_prompt", {"prompt": str(node.user_prompt)}, step=step, usage=usage)
    elif Agent.is_model_request_node(node):
        parts = []
        for p in node.request.parts:
            if isinstance(p, ToolReturnPart):
                parts.append({"type": "tool_return", "tool": p.tool_name,
                              "tool_call_id": p.tool_call_id, "content": _clip(p.content)})
            elif isinstance(p, RetryPromptPart):
                parts.append({"type": "retry", "tool": p.tool_name, "content": _clip(p.content)})
            elif isinstance(p, UserPromptPart):
                parts.append({"type": "user_prompt", "content": _clip(p.content)})
        record(deps, "model_request", {"parts": parts}, step=step, usage=usage)
    elif Agent.is_call_tools_node(node):
        parts = []
        for p in node.model_response.parts:
            if isinstance(p, ToolCallPart):
                parts.append({"type": "tool_call", "tool": p.tool_name,
                              "tool_call_id": p.tool_call_id, "args": p.args_as_dict()})
            elif isinstance(p, TextPart):
                parts.append({"type": "text", "content": _clip(p.content)})
            elif isinstance(p, ThinkingPart):
                parts.append({"type": "thinking", "chars": len(p.content or "")})
        record(deps, "model_response",
               {"model_name": node.model_response.model_name, "parts": parts},
               step=step, usage=usage)
    elif Agent.is_end_node(node):
        output = node.data.output
        dumped = output.model_dump() if hasattr(output, "model_dump") else str(output)
        record(deps, "final_output", {"output": dumped}, step=step, usage=usage)
