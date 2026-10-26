import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


_BEARER = HTTPBearer(auto_error=False)
TOKEN_LIFETIME_SECONDS = 60 * 60 * 8


@dataclass(frozen=True)
class User:
    username: str
    role: str
    psychiatrist_id: int | None = None


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _secret() -> bytes:
    secret = os.getenv("JWT_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="JWT_SECRET must be configured with at least 32 characters")
    return secret.encode("utf-8")


def authenticate(username: str, password: str) -> User | None:
    raw_users = os.getenv("AUTH_USERS_JSON", "[]")
    try:
        users: Any = json.loads(raw_users)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail="AUTH_USERS_JSON is not valid JSON") from exc
    if not isinstance(users, list):
        raise HTTPException(status_code=503, detail="AUTH_USERS_JSON must be a list")
    for account in users:
        if not isinstance(account, dict):
            continue
        expected_username = account.get("username")
        expected_password = account.get("password")
        role = account.get("role")
        if not isinstance(expected_username, str) or not isinstance(expected_password, str):
            continue
        if not hmac.compare_digest(username, expected_username):
            continue
        if len(expected_password) < 12:
            raise HTTPException(
                status_code=503,
                detail="Configured account passwords must contain at least 12 characters",
            )
        if not hmac.compare_digest(password, expected_password):
            return None
        psychiatrist_id = account.get("psychiatrist_id")
        if role == "Psychiatrist" and not isinstance(psychiatrist_id, int):
            raise HTTPException(status_code=503, detail="Psychiatrist account needs a numeric psychiatrist_id")
        if role not in {"Admin", "Psychiatrist"}:
            raise HTTPException(status_code=503, detail="Configured account has an unsupported role")
        return User(username, role, psychiatrist_id)
    return None


def create_access_token(user: User) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + TOKEN_LIFETIME_SECONDS,
    }
    if user.psychiatrist_id is not None:
        payload["psychiatrist_id"] = user.psychiatrist_id
    signing_input = f"{_b64encode(json.dumps(header, separators=(',', ':')).encode())}.{_b64encode(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(_secret(), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64encode(signature)}"


def _decode_access_token(token: str) -> User:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}"
        expected = hmac.new(_secret(), signing_input.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64decode(encoded_signature)):
            raise ValueError("Invalid signature")
        header = json.loads(_b64decode(encoded_header))
        payload = json.loads(_b64decode(encoded_payload))
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise ValueError("Invalid token header")
        if not isinstance(payload.get("exp"), int) or payload["exp"] <= int(time.time()):
            raise ValueError("Expired token")
        username = payload.get("sub")
        role = payload.get("role")
        psychiatrist_id = payload.get("psychiatrist_id")
        if not isinstance(username, str) or role not in {"Admin", "Psychiatrist"}:
            raise ValueError("Invalid token claims")
        if role == "Psychiatrist" and not isinstance(psychiatrist_id, int):
            raise ValueError("Missing psychiatrist ID")
        return User(username, role, psychiatrist_id)
    except HTTPException:
        raise
    except (
        AttributeError,
        binascii.Error,
        UnicodeDecodeError,
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_BEARER),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return _decode_access_token(credentials.credentials)


def require_role(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency
