from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_session import ChatSession


class ChatSessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_uid(self, chat_uid: UUID) -> ChatSession | None:
        result = await self.session.execute(
            select(ChatSession).where(
                ChatSession.uid == chat_uid,
                ChatSession.is_delete.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def add(self, chat_session: ChatSession) -> ChatSession:
        self.session.add(chat_session)
        await self.session.commit()
        await self.session.refresh(chat_session)
        return chat_session
