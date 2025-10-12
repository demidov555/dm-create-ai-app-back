# from fastapi import APIRouter
# from db import messages as db_messages
# from pydantic import BaseModel
# from typing import Optional

# router = APIRouter()


# class Message(BaseModel):
#     project_id: int
#     user_id: int
#     role: str
#     message: str
#     timestamp: Optional[str]


# @router.get("/messages/{project_id}/{user_id}")
# def get_messages(project_id: int, user_id: int):
#     return db_messages.get_messages(project_id, user_id)


# @router.post("/messages")
# def create_message(msg: Message):
#     return db_messages.insert_message(msg)
