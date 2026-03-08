import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models.schemas import ChatRequest

router = APIRouter(tags=["chat"])
log = logging.getLogger(__name__)


@router.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or uuid.uuid4().hex[:12]
    request_id = uuid.uuid4().hex[:8]

    # Create run directory
    run_dir = settings.RUNS_DIR / session_id / request_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "figures").mkdir(exist_ok=True)
    (run_dir / "logs").mkdir(exist_ok=True)

    # Resolve uploaded file path if file_id provided
    file_path = None
    if req.file_id:
        upload_dir = settings.UPLOADS_DIR / req.file_id
        if upload_dir.exists():
            files = list(upload_dir.glob("*.xlsx")) + list(upload_dir.glob("*.xls"))
            if files:
                file_path = str(files[0].resolve())

    async def event_stream():
        # Send session init
        yield _sse("session_init", {"session_id": session_id, "request_id": request_id})

        try:
            from app.agent.orchestrator import run_agent

            async def emit_event(event: dict):
                pass  # Events are collected via the queue

            queue: asyncio.Queue = asyncio.Queue()

            async def queue_callback(event: dict):
                await queue.put(event)

            # Run agent in background task
            async def _run():
                try:
                    await run_agent(
                        message=req.message,
                        session_id=session_id,
                        request_id=request_id,
                        file_path=file_path,
                        outcomes=None,
                        event_callback=queue_callback,
                    )
                except Exception as e:
                    log.exception("Agent error")
                    await queue.put({"event": "error", "data": {"message": str(e)}})
                finally:
                    await queue.put(None)  # Sentinel

            task = asyncio.create_task(_run())

            while True:
                event = await queue.get()
                if event is None:
                    break
                yield _sse(event["event"], event["data"])

            await task

        except Exception as e:
            log.exception("Chat endpoint error")
            yield _sse("error", {"message": str(e)})

        yield _sse("done", {"session_id": session_id, "request_id": request_id})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
