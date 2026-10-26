from fastapi import APIRouter, Depends, HTTPException

from backend.schemas import LoginRequest, TokenResponse
from backend.security import User, authenticate, create_access_token, current_user


router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(
        access_token=create_access_token(user),
        user={
            "username": user.username,
            "role": user.role,
            "psychiatrist_id": user.psychiatrist_id,
        },
    )


@router.get("/me")
def get_current_user(user: User = Depends(current_user)) -> dict[str, str | int | None]:
    return {
        "username": user.username,
        "role": user.role,
        "psychiatrist_id": user.psychiatrist_id,
    }
