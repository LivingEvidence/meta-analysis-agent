import json
import logging
from typing import Any

from app.services.docker_runner import execute_r_analysis
from app.services.excel_parser import parse_outcomes
from app.services.file_manager import read_artifact, write_artifact

log = logging.getLogger(__name__)


def build_tool_definitions(session_id: str, request_id: str, file_path: str | None) -> list[dict]:
    """Build tool definitions for the Claude Agent SDK.

    Returns a list of tool dicts in the Anthropic tool-use format.
    The actual execution is handled by ``handle_tool_call``.
    """
    tools = [
        {
            "name": "doc_writer",
            "description": (
                "Write content to an artifact file within the current analysis run. "
                "Use this to write final.json, report.Rmd, or any other output files."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Relative path within the run directory (e.g., 'final.json', 'report.Rmd')",
                    },
                    "content": {"type": "string", "description": "File content to write"},
                },
                "required": ["filename", "content"],
            },
        },
        {
            "name": "doc_reader",
            "description": "Read content from an artifact file within the current analysis run.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Relative path within the run directory",
                    },
                },
                "required": ["filename"],
            },
        },
        {
            "name": "run_r_analysis",
            "description": (
                "Execute the R meta-analysis script for a single outcome via Docker. "
                "Returns the structured JSON results including studies, pooled estimates, "
                "heterogeneity, publication bias, and leave-one-out sensitivity analysis."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "outcome_name": {"type": "string", "description": "Sheet name for the outcome (e.g., 'OS')"},
                    "full_name": {"type": "string", "description": "Full descriptive name (e.g., 'Overall Survival')"},
                    "measure": {
                        "type": "string",
                        "enum": ["HR", "RR", "OR", "RD", "MD", "SMD"],
                        "description": "Effect measure code",
                    },
                    "data_type": {
                        "type": "string",
                        "enum": ["pre", "raw"],
                        "description": "Data format: 'pre' for pre-calculated, 'raw' for event counts",
                    },
                    "excel_path": {"type": "string", "description": "Absolute path to the Excel file"},
                },
                "required": ["outcome_name", "full_name", "measure", "data_type", "excel_path"],
            },
        },
        {
            "name": "read_outcomes",
            "description": (
                "Parse the Outcomes index sheet from an Excel file. "
                "Returns a JSON list of available outcomes with their names, measures, and data types."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "excel_path": {"type": "string", "description": "Absolute path to the Excel file"},
                },
                "required": ["excel_path"],
            },
        },
    ]
    return tools


async def handle_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    session_id: str,
    request_id: str,
    file_path: str | None,
) -> str:
    """Execute a tool call and return the result as a string."""
    base_dir = f"runs/{session_id}/{request_id}"

    if tool_name == "doc_writer":
        path = write_artifact(base_dir, tool_input["filename"], tool_input["content"])
        return json.dumps({"status": "ok", "path": path})

    elif tool_name == "doc_reader":
        try:
            content = read_artifact(base_dir, tool_input["filename"])
            return content
        except FileNotFoundError as e:
            return json.dumps({"error": str(e)})

    elif tool_name == "run_r_analysis":
        excel = tool_input.get("excel_path", file_path)
        if not excel:
            return json.dumps({"error": "No Excel file path provided"})
        output_dir = f"{base_dir}/figures/{tool_input['outcome_name']}"
        result = await execute_r_analysis(
            excel_path=excel,
            sheet_name=tool_input["outcome_name"],
            measure=tool_input["measure"],
            data_type=tool_input["data_type"],
            full_name=tool_input["full_name"],
            output_dir=output_dir,
        )
        return json.dumps(result, default=str)

    elif tool_name == "read_outcomes":
        excel = tool_input.get("excel_path", file_path)
        if not excel:
            return json.dumps({"error": "No Excel file path provided"})
        result = parse_outcomes(excel)
        return json.dumps(result, default=str)

    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
