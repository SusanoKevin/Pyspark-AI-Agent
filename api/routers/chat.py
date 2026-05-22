import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.deps import get_agent, get_current_user
from api.limiter import limiter
from api.models import ChatRequest
from src.prompt_guard import validate_message
from src.security import UserContext

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stream")
@limiter.limit("10/minute")
async def chat_stream(
    body: ChatRequest,
    request: Request,
    user: UserContext = Depends(get_current_user),
):
    try:
        validated = validate_message(body.message)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    agent = get_agent(request)

    async def generate():
        try:
            async for event in agent.astream_events(validated, user=user):
                yield f"data: {json.dumps(event)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.exception("Chat stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Model error: {e}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
