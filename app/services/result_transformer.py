import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.models.final_json import FinalJSON, OutcomeAnalysis

log = logging.getLogger(__name__)


def assemble_final_json(
    session_id: str,
    request_id: str,
    outcome_results: list[dict],
    metadata: dict | None = None,
) -> dict:
    """Assemble individual outcome results into a complete final.json dict."""
    outcomes = []
    for result in outcome_results:
        try:
            outcome = OutcomeAnalysis(**result)
            outcomes.append(outcome)
        except Exception as e:
            log.warning("Skipping outcome due to validation error: %s", e)

    final = FinalJSON(
        session_id=session_id,
        request_id=request_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        outcomes=outcomes,
        metadata=metadata or {},
    )
    return final.model_dump()


def validate_and_fix_final_json(raw_json: dict) -> dict:
    """Validate agent-produced final.json against schema, attempt to fix common issues."""
    try:
        final = FinalJSON(**raw_json)
        return final.model_dump()
    except Exception as e:
        log.warning("final.json validation failed, attempting fixup: %s", e)
        # Try to fix common issues
        if "outcomes" in raw_json and isinstance(raw_json["outcomes"], list):
            fixed_outcomes = []
            for o in raw_json["outcomes"]:
                if isinstance(o, dict):
                    # Ensure required fields have defaults
                    o.setdefault("figures", {})
                    o.setdefault("leave_one_out", [])
                    o.setdefault("is_ratio", o.get("measure", "") in ("HR", "RR", "OR"))
                    fixed_outcomes.append(o)
            raw_json["outcomes"] = fixed_outcomes
        raw_json.setdefault("session_id", "")
        raw_json.setdefault("request_id", "")
        raw_json.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        raw_json.setdefault("metadata", {})
        return raw_json
