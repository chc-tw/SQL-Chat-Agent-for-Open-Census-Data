from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from app.models.auth import UserInfo
from app.settings import auth_settings


def verify_credentials(username: str, password: str) -> bool:
    users = json.loads(auth_settings.users)
    for user in users:
        if user["username"] == username and user["password"] == password:
            return True
    return False


def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        hours=auth_settings.jwt_expiration_hours
    )
    payload = {"sub": username, "exp": expire}
    return jwt.encode(
        payload, auth_settings.jwt_secret, algorithm=auth_settings.jwt_algorithm
    )


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token, auth_settings.jwt_secret, algorithms=[auth_settings.jwt_algorithm]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


async def get_current_user(request: Request) -> UserInfo:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )
    token = auth_header.split(" ", 1)[1]
    username = decode_token(token)
    return UserInfo(username=username)
