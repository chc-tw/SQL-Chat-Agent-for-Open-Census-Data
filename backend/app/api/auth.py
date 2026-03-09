from fastapi import APIRouter, Depends, HTTPException, status

from app.models.auth import LoginRequest, LoginResponse, UserInfo
from app.services.auth import create_token, get_current_user, verify_credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    if not verify_credentials(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_token(request.username)
    return LoginResponse(access_token=token)


@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)):
    return user
