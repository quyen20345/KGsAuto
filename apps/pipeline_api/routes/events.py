import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from apps.pipeline_api import runner

router = APIRouter(prefix="/api/pipeline", tags=["events"])


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: str):
    async def event_generator():
        queue = runner.subscribe(run_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    continue
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "status" and event.get("status") in ("completed", "failed"):
                    break
        finally:
            runner.unsubscribe(run_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
