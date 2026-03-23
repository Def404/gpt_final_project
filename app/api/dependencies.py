from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.api.api_key import validate
from app.database import get_session
from app.repositories.document_repository import DocumentRepository
from app.repositories.document_vector_repository import DocumentVectorRepository


async def get_document_vector_repository(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> DocumentVectorRepository:
    """Dependency для получения репозитория векторов документов."""
    return DocumentVectorRepository(session)

async def get_document_repository(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> DocumentRepository:
    """Dependency для получения репозитория документов."""
    return DocumentRepository(session)

async def validate_api_key(
    api_key: Annotated[str, Depends(validate)]
) -> str:
    """Dependency для валидации API ключа."""
    return api_key