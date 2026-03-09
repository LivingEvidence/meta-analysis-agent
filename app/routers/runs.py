import io
import logging
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.config import settings

router = APIRouter(tags=["runs"])
log = logging.getLogger(__name__)


@router.get("/runs/{session_id}/{request_id}/download")
async def download_run(session_id: str, request_id: str):
    """Package an entire run directory into a zip archive and return it."""
    run_dir = (settings.RUNS_DIR / session_id / request_id).resolve()
    base = settings.RUNS_DIR.resolve()

    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    # Path traversal guard
    if not str(run_dir).startswith(str(base)):
        raise HTTPException(status_code=403, detail="Access denied")

    # Build zip in memory — runs are typically small (plots + JSON)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(run_dir.rglob("*")):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(run_dir))
    buf.seek(0)

    filename = f"run_{session_id}_{request_id}.zip"
    log.info("Serving zip download: %s (%d bytes)", filename, buf.getbuffer().nbytes)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
        ".r":   "text/plain",
    }.get(suffix, "application/octet-stream")
