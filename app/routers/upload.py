import logging
import shutil
import uuid

from fastapi import APIRouter, File, UploadFile

from app.config import settings
from app.models.schemas import OutcomeInfo, UploadResponse
from app.services.excel_parser import parse_outcomes

router = APIRouter(tags=["upload"])
log = logging.getLogger(__name__)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    file_id = uuid.uuid4().hex[:12]
    dest_dir = settings.UPLOADS_DIR / file_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file.filename

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    log.info("Uploaded %s -> %s", file.filename, dest_path)

    raw_outcomes = parse_outcomes(str(dest_path))
    outcomes = [
        OutcomeInfo(
            name=str(o.get("name", "")),
            full_name=str(o.get("full_name", "")),
            measure=str(o.get("measure", "")),
            data_type=str(o.get("data_type", "")),
        )
        for o in raw_outcomes.get("outcomes", [])
    ]

    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        path=str(dest_path.resolve()),
        outcomes=outcomes,
    )
