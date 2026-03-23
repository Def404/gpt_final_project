from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_by_chat_uid(self, chat_uid: UUID) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.chat_uid == chat_uid)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())
