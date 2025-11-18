import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.chat_agent import ChatAgent

router = APIRouter()


class ChatRequest(BaseModel):
    user_request: str
    user_id: int | None = None
    user_email: str | None = None
    messages: list[dict] | None = None
    selected_course_ids: list[int] | None = None


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat response from ChatAgent
    """
    try:
        chat_agent = ChatAgent()

        async def generate():
            async for chunk in chat_agent.chat(
                user_request=request.user_request,
                user_id=request.user_id,
                user_email=request.user_email,
                messages=request.messages,
                selected_course_ids=request.selected_course_ids,
            ):
                # Yield each chunk as SSE (Server-Sent Events) format
                yield f"data: {json.dumps({'chunk': chunk})}\t\t"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
