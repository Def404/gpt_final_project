from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.models.document import Document


class DocumentRepository:
    """Репозиторий для работы с документами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_uid(self, document_uid: UUID) -> Document:
        """Получить документ по ID."""
        result = await self.session.execute(
            select(Document).where(Document.uid == document_uid)
        )
        return result.scalar_one_or_none()