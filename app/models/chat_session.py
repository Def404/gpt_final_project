from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean
from sqlalchemy.dialects.postgresql import JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base, uuid_pk

if TYPE_CHECKING:
    from models.message import Message


class ChatSession(Base):
    __table_args__ = {"schema": "chat"}

    uid: Mapped[uuid_pk]
    title: Mapped[str] = mapped_column(TEXT, nullable=False)
    is_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    chat_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
    )

    def __str__(self):
        return f"{self.__class__.__name__}(uid={self.uid}, title={self.title})"

    def __repr__(self):
        return str(self)
