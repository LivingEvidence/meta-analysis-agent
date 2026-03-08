from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class OutcomeInfo(BaseModel):
    name: str
    full_name: str
    measure: str  # HR, RR, OR, RD, MD, SMD
    data_type: str  # "pre" or "raw"


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    file_id: str | None = None


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    path: str
    outcomes: list[OutcomeInfo]


class SSEEvent(BaseModel):
    event: str
    data: dict[str, Any]
