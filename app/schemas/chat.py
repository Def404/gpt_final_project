from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageRequest(BaseModel):
    chat_uid: UUID | None = None
    message_text: str = Field(min_length=1)
    message_metadata: dict | None = None


class ChatSessionResponse(BaseModel):
    uid: UUID
    title: str
    is_delete: bool
    chat_metadata: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    uid: UUID
    chat_uid: UUID
    reply_uid: UUID | None
    sender: str
    message_text: str
    message_metadata: dict | None
    status: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    bot_message: MessageResponse
    chat: ChatSessionResponse

    model_config = ConfigDict(from_attributes=True)
