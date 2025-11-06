from pydantic import BaseModel
from fastapi import APIRouter, Depends
from app.auth.auth import get_current_user_firebase, create_jwt

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    uid: str
    phone: str | None = None


# ВАЖНО: id_token передаётся в заголовке Authorization: Bearer <id_token>
@router.post("/login", response_model=TokenResponse)
async def login(user_data=Depends(get_current_user_firebase)):
    uid = user_data["uid"]
    phone = user_data.get("phone_number")

    jwt_token = create_jwt({"uid": uid, "phone": phone})

    return TokenResponse(
        access_token=jwt_token,
        uid=uid,
        phone=phone
    )
