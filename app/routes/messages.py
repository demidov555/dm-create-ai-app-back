from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.agents.product_manager import get_ai_response
from app.db import messages as db_messages
from pydantic import BaseModel, Field
import json

router = APIRouter()


class Message(BaseModel):
    project_id: int
    user_id: int
    role: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


@router.get("/history_messages/{project_id}")
def get_messages(project_id: int):
    return db_messages.get_messages(project_id)


@router.post("/chat_message")
async def create_message(message_request: Message):
    async def event_stream():
        # db_messages.save_message(message_request)

        context = db_messages.get_messages_by_project(
            message_request.project_id)

        ai_response = await get_ai_response(
            message_request.project_id,
            message_request.user_id,
            message_request.message,
            context,
        )

        assistant_response = Message(
            project_id=message_request.project_id,
            message=ai_response,
            role="agent",
            timestamp=datetime.utcnow(),
            user_id=message_request.user_id,
        )

        # db_messages.save_message(assistant_response)

        yield f"data: {json.dumps(assistant_response.model_dump(mode='json'))}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
