from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from core.config import (
    MAX_ASSISTANT_MESSAGE_CHARS,
    MAX_MESSAGE_CHARS,
    MAX_MESSAGES_PER_REQUEST,
    MAX_SESSION_IDS_PER_DELETE,
)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: Optional[str] = Field(default="", max_length=MAX_ASSISTANT_MESSAGE_CHARS)
    parts: Optional[List[Dict[str, Any]]] = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_text_content(self) -> "Message":
        text = self.content or ""
        if self.parts:
            for part in self.parts:
                if part.get("type") not in (None, "text"):
                    raise ValueError("Only text message parts are supported.")
                part_text = part.get("text", "")
                if not isinstance(part_text, str):
                    raise ValueError("Message part text must be a string.")
                text += part_text

        limit = MAX_MESSAGE_CHARS if self.role == "user" else MAX_ASSISTANT_MESSAGE_CHARS
        if len(text) > limit:
            raise ValueError(f"Message text exceeds the {limit}-character limit.")
        return self

class ChatRequest(BaseModel):
    messages: List[Message] = Field(min_length=1, max_length=MAX_MESSAGES_PER_REQUEST)
    session_id: str

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        parsed = UUID(value)
        if str(parsed) != value.lower():
            raise ValueError("session_id must be a canonical UUID.")
        return str(parsed)

    @model_validator(mode="after")
    def require_latest_user_message(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("The latest message must have the user role.")
        return self


class AdminChatDeleteRequest(BaseModel):
    session_ids: List[str] = Field(default_factory=list, max_length=MAX_SESSION_IDS_PER_DELETE)
    delete_all: bool = False
    confirmation: Optional[str] = None

    @field_validator("session_ids")
    @classmethod
    def validate_session_ids(cls, values: List[str]) -> List[str]:
        return list(dict.fromkeys(str(UUID(value)) for value in values))

    @model_validator(mode="after")
    def validate_delete_scope(self) -> "AdminChatDeleteRequest":
        if self.delete_all:
            if self.session_ids:
                raise ValueError("Use either session_ids or delete_all, not both.")
            if self.confirmation != "DELETE_ALL_CHATS":
                raise ValueError("Deleting all chats requires confirmation DELETE_ALL_CHATS.")
        elif not self.session_ids:
            raise ValueError("Provide at least one session ID.")
        return self
