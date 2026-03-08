"""Agent orchestration using the Claude Agent SDK.

The backend keeps SDK setup minimal and defers the actual workflow to the
project skill. It only passes run context into Claude Code and forwards SDK
events to the frontend.
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Coroutine

from app.agent.message_logger import classify_message, log_message
from app.config import settings
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

log = logging.getLogger(__name__)

# Type alias for the SSE event callback
EventCallback = Callable[[dict], Coroutine[Any, Any, None]]


def _build_claude_env() -> dict[str, str]:
    """Build environment variables for the Claude CLI subprocess."""
    env: dict[str, str] = {}

    if settings.ANTHROPIC_API_KEY:
        env["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY

    if settings.CLAUDE_CODE_USE_FOUNDRY:
        env["CLAUDE_CODE_USE_FOUNDRY"] = "1"

    if settings.ANTHROPIC_FOUNDRY_API_KEY:
        env["ANTHROPIC_FOUNDRY_API_KEY"] = settings.ANTHROPIC_FOUNDRY_API_KEY

    if settings.ANTHROPIC_FOUNDRY_RESOURCE:
        env["ANTHROPIC_FOUNDRY_RESOURCE"] = settings.ANTHROPIC_FOUNDRY_RESOURCE
        env.setdefault(
            "ANTHROPIC_BASE_URL",
            f"https://{settings.ANTHROPIC_FOUNDRY_RESOURCE}.services.ai.azure.com",
        )

    if settings.ANTHROPIC_DEFAULT_SONNET_MODEL:
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = settings.ANTHROPIC_DEFAULT_SONNET_MODEL

    if settings.ANTHROPIC_DEFAULT_HAIKU_MODEL:
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = settings.ANTHROPIC_DEFAULT_HAIKU_MODEL

    if settings.ANTHROPIC_DEFAULT_OPUS_MODEL:
        env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = settings.ANTHROPIC_DEFAULT_OPUS_MODEL

    return env


async def run_agent(
    message: str,
    session_id: str,
    request_id: str,
    file_path: str | None,
    outcomes: list[dict] | None,
    event_callback: EventCallback,
) -> None:
    """Run the skill-driven meta-analysis agent and stream events via callback."""
    project_root = Path(__file__).resolve().parents[2]
    prompt = _compose_prompt(message, file_path, outcomes)

    options = ClaudeAgentOptions(
        allowed_tools=["Skill", "Read"],
        max_turns=settings.MAX_AGENT_TURNS,
        model=settings.AGENT_MODEL,
        cwd=str(project_root),
        env=_build_claude_env(),
        permission_mode="bypassPermissions",
        setting_sources=["user", "project"],
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        log.info("Agent text: %s", block.text[:100])
                    elif isinstance(block, ToolUseBlock):
                        log.info("Agent tool_use: %s", block.name)

            elif isinstance(msg, ResultMessage):
                log.info(
                    "Agent finished: turns=%s cost=$%s",
                    getattr(msg, "num_turns", "?"),
                    getattr(msg, "total_cost_usd", "?"),
                )

            # Classify and emit SSE events
            events = classify_message(msg)
            for event in events:
                await event_callback(event)

            # Log to file
            log_message(msg, session_id, request_id)

    # After agent completes, check if final.json exists and emit visualization event
    await _emit_visualization_if_ready(session_id, request_id, event_callback)


async def _emit_visualization_if_ready(
    session_id: str,
    request_id: str,
    event_callback: EventCallback,
) -> None:
    """If final.json exists, emit a visualization event."""
    from app.services.file_manager import read_artifact, write_artifact

    try:
        content = read_artifact(f"runs/{session_id}/{request_id}", "final.json")
        data = json.loads(content)
        await event_callback({"event": "visualization", "data": data})
    except (FileNotFoundError, json.JSONDecodeError):
        log.info("No valid final.json found after agent run")

    # Check for report.Rmd and emit artifact event
    try:
        read_artifact(f"runs/{session_id}/{request_id}", "report.Rmd")
        await event_callback(
            {
                "event": "artifact",
                "data": {
                    "type": "report",
                    "path": f"/api/runs/{session_id}/{request_id}/report.Rmd",
                },
            }
        )
    except FileNotFoundError:
        pass


def _compose_prompt(
    message: str,
    file_path: str | None,
    outcomes: list[dict] | None,
) -> str:
    """Compose a small prompt and let the project skill drive execution."""
    parts = [
        "Use the project's `meta-analysis` skill for this request.",
        "",
        f"User request: {message}",
    ]

    if file_path:
        parts.extend(["", f"Uploaded Excel file: {file_path}"])

    if outcomes:
        parts.extend(["", "Available outcomes:"])
        for o in outcomes:
            parts.append(f"  - {o.get('name')}: {o.get('full_name')} ({o.get('measure')}, {o.get('data_type')})")

    return "\n".join(parts)

