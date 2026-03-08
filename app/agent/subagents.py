from app.agent.prompts import ANALYZER_PROMPT, PLANNER_PROMPT, WRITER_PROMPT_TEMPLATE


def get_subagent_definitions(session_id: str, request_id: str) -> dict:
    """Build subagent definition dicts for the Claude Agent SDK.

    Each subagent is a dict with keys: description, prompt, tools, model.
    The exact shape depends on the Claude Agent SDK version; this returns
    plain dicts that the orchestrator maps into the SDK's AgentDefinition.
    """
    return {
        "planner": {
            "description": (
                "Planning specialist for meta-analysis workflows. Use this agent to "
                "decide which outcomes to analyze, determine the analysis sequence, "
                "validate data requirements, and create an execution plan."
            ),
            "prompt": PLANNER_PROMPT,
            "tools": ["read_outcomes", "doc_reader"],
            "model": "sonnet",
        },
        "analyzer": {
            "description": (
                "Statistical analysis executor. Use this agent to run R-based "
                "meta-analyses for individual outcomes and interpret the results."
            ),
            "prompt": ANALYZER_PROMPT,
            "tools": ["run_r_analysis", "doc_reader", "doc_writer"],
            "model": "sonnet",
        },
        "writer": {
            "description": (
                "Report and visualization data writer. Use this agent to compile "
                "analysis results into final.json for visualization and report.Rmd "
                "for reproducibility."
            ),
            "prompt": WRITER_PROMPT_TEMPLATE.format(
                session_id=session_id,
                request_id=request_id,
            ),
            "tools": ["doc_reader", "doc_writer"],
            "model": "sonnet",
        },
    }
