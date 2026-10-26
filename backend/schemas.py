from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=500)


class CreatePsychiatristRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: str = Field(min_length=3, max_length=254)
    field: str = Field(min_length=2, max_length=200)
    initial_password: str = Field(min_length=12, max_length=128)

    @field_validator("full_name", "email", "field")
    @classmethod
    def trim_required_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if value.count("@") != 1 or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return value.casefold()


class UpdateCapacityRequest(BaseModel):
    max_patients: int = Field(ge=0, le=1000)


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)


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


class EditChatMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class PatientNoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Note cannot be blank")
        return value


class PatientNote(BaseModel):
    note_id: int
    patient_id: int
    psychiatrist_id: int
    text: str
    created_at: datetime
    updated_at: datetime


class ChatMessage(BaseModel):
    message_id: int
    telegram_id: int
    psychiatrist_id: int
    sender_type: Literal["patient", "psychiatrist"]
    text: str
    timestamp: datetime
    telegram_message_id: int | None = None
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    deleted_for_psychiatrist: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: dict[str, str | int | bool | None]
