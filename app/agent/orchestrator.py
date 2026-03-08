"""Agent orchestration using the Claude Agent SDK.

The backend is intentionally minimal. It provides run context (paths, IDs)
and lets the project skill drive the entire workflow — including writing R
code, running it in Docker, debugging errors, and assembling final.json.
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
    event_callback: EventCallback,
) -> None:
    """Run the skill-driven meta-analysis agent and stream events via callback."""
    project_root = Path(__file__).resolve().parents[2]
    run_dir = project_root / "runs" / session_id / request_id
    prompt = _compose_prompt(message, file_path, str(run_dir))

    options = ClaudeAgentOptions(
        # The agent needs Bash to run docker commands, Write to save R scripts,
        # Read to inspect files, and Skill to load the meta-analysis skill.
        allowed_tools=["Bash", "Write", "Read", "Skill"],
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
    """If final.json exists in the run directory, emit a visualization event."""
    run_dir = Path("runs") / session_id / request_id

    final_json_path = run_dir / "final.json"
    if final_json_path.exists():
        try:
            data = json.loads(final_json_path.read_text())
            await event_callback({"event": "visualization", "data": data})
        except json.JSONDecodeError:
            log.warning("final.json exists but is not valid JSON: %s", final_json_path)
    else:
        log.info("No final.json found after agent run at %s", final_json_path)

    # Check for report.Rmd and emit artifact event
    report_path = run_dir / "report.Rmd"
    if report_path.exists():
        await event_callback(
            {
                "event": "artifact",
                "data": {
                    "type": "report",
                    "path": f"/api/runs/{session_id}/{request_id}/report.Rmd",
                },
            }
        )


def _compose_prompt(
    message: str,
    file_path: str | None,
    run_dir: str,
) -> str:
    """Compose the agent prompt with run context only.

    The skill drives all workflow logic. The prompt just provides paths and IDs
    so the agent knows where to write outputs.
    """
    parts = [
        "Use the project's `meta-analysis` skill for this request.",
        "",
        f"User request: {message}",
        "",
        "Run context:",
        f"  Output directory (absolute): {run_dir}",
        f"  Docker image: {settings.DOCKER_IMAGE_NAME}",
    ]

    if file_path:
        parts.extend(["", f"  Uploaded Excel file (absolute): {file_path}"])

    parts.extend([
        "",
        "Write final.json to the output directory when the analysis is complete.",
        "The output directory and all required subdirectories already exist.",
    ])

    return "\n".join(parts)
