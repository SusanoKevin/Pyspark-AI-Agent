import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.deps import get_agent
from api.models import TaskRequest
from src.prompt_guard import validate_message

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/task")
async def run_task(body: TaskRequest, request: Request):
    try:
        validated = validate_message(body.task)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    agent = get_agent(request)

    async def generate():
        try:
            async for event in agent.astream_events(validated):
                yield f"data: {json.dumps(event)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.exception("Task stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Agent error: {e}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
