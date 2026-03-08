import logging
from pathlib import Path

log = logging.getLogger(__name__)


def write_artifact(base_dir: str, filename: str, content: str) -> str:
    """Write content to an artifact file within a run directory."""
    path = Path(base_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    log.info("Written artifact: %s", path)
    return str(path)


def read_artifact(base_dir: str, filename: str) -> str:
    """Read content from an artifact file within a run directory."""
    path = Path(base_dir) / filename
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {path}")
    return path.read_text(encoding="utf-8")


def list_artifacts(base_dir: str) -> list[str]:
    """List all artifact files in a run directory."""
    path = Path(base_dir)
    if not path.exists():
        return []
    return [str(p.relative_to(path)) for p in path.rglob("*") if p.is_file()]
