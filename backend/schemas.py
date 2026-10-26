from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=500)


class AssignCaseRequest(BaseModel):
    telegram_id: int = Field(gt=0)
    psychiatrist_id: int = Field(gt=0)


class ChatMessageRequest(BaseModel):
    telegram_id: int = Field(gt=0)
    psychiatrist_id: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: dict[str, str | int | None]
