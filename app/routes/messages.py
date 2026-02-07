from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.agents.product_manager import get_ai_response
from app.db import messages as db_messages
from pydantic import BaseModel, Field
import asyncio
import json
import uuid
from typing import Dict

router = APIRouter()

project_queues: Dict[uuid.UUID, asyncio.Queue] = {}
project_tasks: Dict[uuid.UUID, asyncio.Task] = {}

KEEP_ALIVE_INTERVAL = 15


class Message(BaseModel):
    project_id: uuid.UUID
    role: str
    message: str
    message_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def dict_with_timestamp(self):
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat() + "Z"
        return data


def _json_default(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def _sse_pack(data: dict, event: str | None = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {json.dumps(data, ensure_ascii=False, default=_json_default)}\n\n"


async def keep_alive_sender(request: Request, queue: asyncio.Queue):
    while True:
        if await request.is_disconnected():
            break
        await queue.put(": keep-alive\n\n")
        await asyncio.sleep(KEEP_ALIVE_INTERVAL)


async def generate_ai_response(user_msg: Message, queue: asyncio.Queue):
    project_id = user_msg.project_id
    full_message = []

    try:
        context = db_messages.get_all_messages(project_id)
        message_id = str(uuid.uuid4())

        async for chunk in get_ai_response(
            project_id=project_id,
            user_message=user_msg.message,
            history=context,
        ):
            full_message.append(chunk)
            ai_msg = Message(
                project_id=project_id,
                role="agent",
                message=chunk,
                message_id=message_id,
                timestamp=datetime.utcnow(),
            )
            await queue.put(_sse_pack(ai_msg.dict_with_timestamp()))

        final_text = "".join(full_message)
        final_msg = Message(
            project_id=project_id,
            role="agent",
            message=final_text,
            timestamp=datetime.utcnow(),
        )
        db_messages.save_message(final_msg)

        await queue.put(_sse_pack({"message_id": message_id}, event="end"))

    except asyncio.CancelledError:
        if full_message:
            partial_message = "".join(full_message)

            partial_msg = Message(
                project_id=project_id,
                role="agent",
                message=partial_message,
                timestamp=datetime.utcnow(),
            )

            db_messages.save_message(partial_msg)
        return

    except Exception as e:
        error_msg = Message(
            project_id=project_id,
            role="system",
            message=f"AI error: {str(e)}",
            message_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
        )
        await queue.put(_sse_pack(error_msg.dict_with_timestamp()))

    finally:
        # ✓ Очищаем таск после завершения
        project_tasks.pop(project_id, None)


# === GET: SSE-поток ===
@router.get("/chat_stream/{project_id}")
async def chat_stream(project_id: uuid.UUID, request: Request):
    if project_id not in project_queues:
        project_queues[project_id] = asyncio.Queue()

    queue = project_queues[project_id]

    async def event_generator():
        keep_alive_task = asyncio.create_task(keep_alive_sender(request, queue))

        try:
            yield _sse_pack({"event": "connected", "project_id": project_id})

            while True:
                if await request.is_disconnected():
                    break

                message = await queue.get()
                yield message

        finally:
            keep_alive_task.cancel()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# === POST: Приём сообщения + запуск AI ===
@router.post("/chat_message")
async def create_message(message_request: Message):
    project_id = message_request.project_id

    if project_id not in project_queues:
        project_queues[project_id] = asyncio.Queue()

    queue = project_queues[project_id]

    message_request.timestamp = datetime.utcnow()
    db_messages.save_message(message_request)

    old_task = project_tasks.get(project_id)
    if old_task and not old_task.done():
        old_task.cancel()

    task = asyncio.create_task(generate_ai_response(message_request, queue))
    project_tasks[project_id] = task

    return {"status": "ok"}


# === POST: Отмена AI генерации ===
@router.post("/chat_cancel/{project_id}")
async def cancel_stream(project_id: uuid.UUID):
    task = project_tasks.get(project_id)

    if task and not task.done():
        task.cancel()
        return {"status": "cancelled"}

    return {"status": "already_finished"}


# === GET: История сообщений ===
@router.get("/history_messages/{project_id}")
def get_messages(project_id: uuid.UUID):
    return db_messages.get_all_messages(project_id)
