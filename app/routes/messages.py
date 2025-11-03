from datetime import datetime
from pprint import pprint
from fastapi import APIRouter
from app.agents.product_manager import get_ai_response
from app.db import messages as db_messages
from pydantic import BaseModel, Field
from app.sockets import sio

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


@sio.on("chat_message")
async def create_message(sid, message_request):
    message_request = Message(**message_request)

    await sio.enter_room(sid, message_request.project_id)

    # Получаем ответ от Groq
    context = db_messages.get_messages_by_project(message_request.project_id)
    groq_response = await get_ai_response(message_request.project_id, message_request.user_id, message_request.message, context)

    # Сохраняем ответ
    assistant_msg = Message(
        project_id=message_request.project_id,
        message=groq_response,
        role="agent",
        timestamp=datetime.utcnow().isoformat(),
        user_id=message_request.user_id,
    )
    # db_messages.save_message(assistant_msg)

    await sio.emit("chat_message", assistant_msg.model_dump(mode="json"), room=message_request.project_id)
