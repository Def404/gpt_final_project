from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, uuid_pk

if TYPE_CHECKING:
    from models.chat_session import ChatSession


class Message(Base):
    __table_args__ = {"schema": "chat"}

    uid: Mapped[uuid_pk]
    chat_uid: Mapped[UUID] = mapped_column(ForeignKey("chat.chat_sessions.uid"), nullable=False)
    reply_uid: Mapped[UUID | None] = mapped_column(ForeignKey("chat.messages.uid"), nullable=True)
    sender: Mapped[str] = mapped_column(TEXT, nullable=False)
    message_text: Mapped[str] = mapped_column(TEXT, nullable=False)
    message_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str | None] = mapped_column(TEXT, nullable=True)

    chat: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    reply_message: Mapped["Message | None"] = relationship(
        "Message",
        remote_side="Message.uid",
        back_populates="child_messages",
    )
    child_messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="reply_message",
    )

    def __str__(self):
        return f"{self.__class__.__name__}(uid={self.uid}, chat_uid={self.chat_uid}, sender={self.sender})"

    def __repr__(self):
        return str(self)
