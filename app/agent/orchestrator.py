"""Agent orchestration using the Claude Agent SDK.

This module wires up the Claude Agent SDK with custom tools and subagents,
runs the main analysis loop, and streams messages back via an async callback.
"""

import json
import logging
from typing import Any, Callable, Coroutine

from app.agent.message_logger import classify_message, log_message
from app.agent.prompts import MAIN_SYSTEM_PROMPT
from app.agent.subagents import get_subagent_definitions
from app.agent.tools import (
    build_sdk_mcp_server,
    build_tool_definitions,
    get_run_analysis_results,
    init_run_result_store,
)
from app.config import settings

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
    """Run the meta-analysis agent and stream events via callback.

    This function:
    1. Builds custom tools scoped to this run
    2. Configures subagent definitions
    3. Invokes the Claude Agent SDK
    4. Iterates over streamed messages, classifying them into SSE events
    """
    try:
        from claude_agent_sdk import (
            AgentDefinition,
            ClaudeAgentOptions,
            ClaudeSDKClient,
        )
        from claude_agent_sdk.types import (
            AssistantMessage,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
        )
    except ImportError:
        log.warning("claude_agent_sdk not installed, using mock agent")
        await _run_mock_agent(message, session_id, request_id, file_path, outcomes, event_callback)
        return

    # Build tools and subagents
    init_run_result_store(session_id, request_id)
    tool_defs = build_tool_definitions(session_id, request_id, file_path)
    mcp_server = build_sdk_mcp_server(session_id, request_id, file_path)
    subagent_defs = get_subagent_definitions(session_id, request_id)

    # Map subagent dicts to AgentDefinition instances
    agents = {}
    for name, defn in subagent_defs.items():
        agents[name] = AgentDefinition(
            description=defn["description"],
            prompt=defn["prompt"],
            tools=defn.get("tools", []),
            model=defn.get("model", settings.AGENT_MODEL),
        )

    # Compose the user prompt with context
    prompt = _compose_prompt(message, file_path, outcomes)

    options = ClaudeAgentOptions(
        system_prompt=MAIN_SYSTEM_PROMPT,
        allowed_tools=["Agent"] + [t["name"] for t in tool_defs],
        mcp_servers={"meta_analysis": mcp_server},
        agents=agents,
        max_turns=settings.MAX_AGENT_TURNS,
        cwd=str((settings.RUNS_DIR / session_id / request_id).resolve()),
        env=_build_claude_env(),
        permission_mode="bypassPermissions",
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
        analysis_results = get_run_analysis_results(session_id, request_id)
        if analysis_results:
            from app.services.result_transformer import assemble_final_json

            data = assemble_final_json(
                session_id,
                request_id,
                analysis_results,
                {"assembled_by": "backend_fallback"},
            )
            write_artifact(f"runs/{session_id}/{request_id}", "final.json", json.dumps(data, indent=2))
            await event_callback({"event": "visualization", "data": data})
            log.info("Assembled final.json from collected run_r_analysis results")
        else:
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
    """Compose the user prompt with context about uploaded data."""
    parts = [message]

    if file_path:
        parts.append(f"\n\nThe user has uploaded an Excel file at: {file_path}")

    if outcomes:
        parts.append("\n\nAvailable outcomes from the file:")
        for o in outcomes:
            parts.append(f"  - {o.get('name')}: {o.get('full_name')} ({o.get('measure')}, {o.get('data_type')})")

    return "\n".join(parts)


async def _run_mock_agent(
    message: str,
    session_id: str,
    request_id: str,
    file_path: str | None,
    outcomes: list[dict] | None,
    event_callback: EventCallback,
) -> None:
    """Fallback when claude_agent_sdk is not installed.

    Runs the analysis directly without the agent layer, useful for testing
    the pipeline end-to-end.
    """
    await event_callback(
        {
            "event": "agent_text",
            "data": {
                "text": "Claude Agent SDK is not installed. Running in mock mode.\n\n"
                "To use the full agent, install the SDK: `pip install claude-agent-sdk`\n\n"
                "I'll attempt to run the analysis directly."
            },
        }
    )

    if not file_path:
        await event_callback({"event": "agent_text", "data": {"text": "No file uploaded. Please upload an Excel file first."}})
        return

    # Parse outcomes directly
    from app.services.excel_parser import parse_outcomes

    result = parse_outcomes(file_path)
    outcome_list = result.get("outcomes", [])

    if not outcome_list:
        await event_callback({"event": "agent_text", "data": {"text": "No outcomes found in the uploaded file."}})
        return

    await event_callback(
        {
            "event": "agent_text",
            "data": {
                "text": f"Found {len(outcome_list)} outcomes. Running analysis for each...\n"
            },
        }
    )

    # Run analysis for each outcome
    from app.services.docker_runner import execute_r_analysis

    all_results = []
    for outcome in outcome_list:
        name = str(outcome.get("name", ""))
        full_name = str(outcome.get("full_name", name))
        measure = str(outcome.get("measure", ""))
        data_type = str(outcome.get("data_type", ""))

        await event_callback(
            {"event": "tool_use", "data": {"tool": "run_r_analysis", "input": {"outcome_name": name}}}
        )

        output_dir = f"runs/{session_id}/{request_id}/figures/{name}"
        r_result = await execute_r_analysis(
            excel_path=file_path,
            sheet_name=name,
            measure=measure,
            data_type=data_type,
            full_name=full_name,
            output_dir=output_dir,
        )

        all_results.append(r_result)
        await event_callback({"event": "tool_result", "data": {"tool": "run_r_analysis"}})

    # Assemble and write final.json
    from app.services.result_transformer import assemble_final_json

    final = assemble_final_json(session_id, request_id, all_results, {"source_file": file_path})
    from app.services.file_manager import write_artifact

    write_artifact(f"runs/{session_id}/{request_id}", "final.json", json.dumps(final, indent=2))

    await event_callback({"event": "visualization", "data": final})
    await event_callback({"event": "agent_text", "data": {"text": "Analysis complete. Results are ready for visualization."}})
