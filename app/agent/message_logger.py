import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def classify_message(msg: Any) -> list[dict]:
    """Convert a Claude Agent SDK message into SSE-compatible event dicts.

    Inspects the message type and content blocks to produce events like
    agent_text, tool_use, subagent_start, done, etc.
    """
    events = []
    msg_type = type(msg).__name__

    if msg_type == "AssistantMessage":
        for block in getattr(msg, "content", []):
            block_type = getattr(block, "type", None)
            if block_type == "text":
                events.append({"event": "agent_text", "data": {"text": block.text}})
            elif block_type == "tool_use":
                if block.name in ("Agent", "Task"):
                    # Subagent invocation
                    input_data = block.input if isinstance(block.input, dict) else {}
                    events.append(
                        {
                            "event": "subagent_start",
                            "data": {
                                "name": input_data.get("subagent_type", input_data.get("description", "unknown")),
                                "task": str(input_data.get("prompt", ""))[:300],
                            },
                        }
                    )
                else:
                    events.append(
                        {
                            "event": "tool_use",
                            "data": {
                                "tool": block.name,
                                "input": _safe_serialize(block.input),
                            },
                        }
                    )

    elif msg_type == "UserMessage":
        for block in getattr(msg, "content", []):
            block_type = getattr(block, "type", None)
            if block_type == "tool_result":
                events.append({"event": "tool_result", "data": {"tool_use_id": getattr(block, "tool_use_id", "")}})

    elif msg_type == "ResultMessage":
        events.append(
            {
                "event": "result",
                "data": {
                    "result": getattr(msg, "result", ""),
                    "cost_usd": getattr(msg, "total_cost_usd", None),
                    "turns": getattr(msg, "num_turns", None),
                    "duration_ms": getattr(msg, "duration_ms", None),
                },
            }
        )

    return events


def log_message(msg: Any, session_id: str, request_id: str) -> None:
    """Append a log entry for a message to the run's log file."""
    log_path = Path(f"runs/{session_id}/{request_id}/logs/agent.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": type(msg).__name__,
    }

    msg_type = type(msg).__name__
    if msg_type == "AssistantMessage":
        blocks = []
        for block in getattr(msg, "content", []):
            bt = getattr(block, "type", "unknown")
            if bt == "text":
                blocks.append({"type": "text", "length": len(block.text)})
            elif bt == "tool_use":
                blocks.append({"type": "tool_use", "name": block.name})
        entry["blocks"] = blocks
    elif msg_type == "ResultMessage":
        entry["result_preview"] = str(getattr(msg, "result", ""))[:200]

    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _safe_serialize(obj: Any) -> Any:
    """Safely serialize an object for JSON, truncating large strings."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, str) and len(obj) > 500:
        return obj[:500] + "... (truncated)"
    return obj
