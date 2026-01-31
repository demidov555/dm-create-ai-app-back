from dotenv import load_dotenv
from firebase_admin import auth as firebase_auth
from fastapi import Depends, HTTPException, Header
import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from .firebase import verify_firebase_token

load_dotenv()

SECRET_KEY = os.getenv("FIREBASE_SECRET_KEY")
ALGORITHM = "HS256"

if not SECRET_KEY:
    raise RuntimeError("Установите SECRET_KEY в .env")

security = HTTPBearer()


def create_jwt(data: dict):
    if not SECRET_KEY:
        raise RuntimeError("Установите SECRET_KEY в .env")

    from datetime import datetime, timedelta
    expire = datetime.utcnow() + timedelta(hours=24)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_firebase(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header")

    id_token = authorization.split("Bearer ")[1]

    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Invalid Firebase token: {str(e)}")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not SECRET_KEY:
        raise RuntimeError("Установите SECRET_KEY в .env")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
