from fastapi import APIRouter, Depends, HTTPException

from backend.database import read_json, transaction, write_json
from backend.schemas import ChangePasswordRequest, LoginRequest, TokenResponse
from backend.security import User, authenticate, create_access_token, current_user, hash_password


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
            "must_change_password": user.must_change_password,
        },
    )


@router.get("/me")
def get_current_user(user: User = Depends(current_user)) -> dict[str, str | int | bool | None]:
    return {
        "username": user.username,
        "role": user.role,
        "psychiatrist_id": user.psychiatrist_id,
        "must_change_password": user.must_change_password,
    }


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(current_user),
) -> TokenResponse:
    if user.role != "Psychiatrist" or not user.must_change_password or user.psychiatrist_id is None:
        raise HTTPException(status_code=403, detail="Password change is not required for this account")
    with transaction():
        psychiatrists = read_json("psychiatrists.json")
        psychiatrist = next(
            (item for item in psychiatrists if item.get("psychiatrist_id") == user.psychiatrist_id),
            None,
        )
        if psychiatrist is None:
            raise HTTPException(status_code=404, detail="Psychiatrist account not found")
        if not psychiatrist.get("must_change_password", False):
            raise HTTPException(status_code=409, detail="Initial password has already been changed")
        psychiatrist["password_hash"] = hash_password(request.new_password)
        psychiatrist["must_change_password"] = False
        write_json("psychiatrists.json", psychiatrists)

    updated_user = User(user.username, user.role, user.psychiatrist_id)
    return TokenResponse(
        access_token=create_access_token(updated_user),
        user={
            "username": updated_user.username,
            "role": updated_user.role,
            "psychiatrist_id": updated_user.psychiatrist_id,
            "must_change_password": False,
        },
    )
