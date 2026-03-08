import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter(tags=["runs"])
log = logging.getLogger(__name__)


@router.get("/runs/{session_id}/{request_id}/{path:path}")
async def get_artifact(session_id: str, request_id: str, path: str):
    file_path = settings.RUNS_DIR / session_id / request_id / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path}")

    # Prevent path traversal
    resolved = file_path.resolve()
    base = (settings.RUNS_DIR / session_id / request_id).resolve()
    if not str(resolved).startswith(str(base)):
        raise HTTPException(status_code=403, detail="Access denied")

    media_type = _guess_media_type(resolved)
    return FileResponse(resolved, media_type=media_type)


def _guess_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".json": "application/json",
        ".rmd": "text/plain",
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".log": "text/plain",
    }.get(suffix, "application/octet-stream")
