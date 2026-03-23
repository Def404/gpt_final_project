from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from api.api_key import validate
from database import get_session
from repositories.chat_session_repository import ChatSessionRepository
from repositories.document_repository import DocumentRepository
from repositories.document_vector_repository import DocumentVectorRepository
from repositories.message_repository import MessageRepository
from services.chat_service import ChatService
from services.send_message_pipeline import SendMessagePipeline, build_pipeline


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


async def get_chat_session_repository(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> ChatSessionRepository:
    return ChatSessionRepository(session)


async def get_message_repository(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> MessageRepository:
    return MessageRepository(session)


def get_send_message_pipeline(
    document_vector_repository: Annotated[DocumentVectorRepository, Depends(get_document_vector_repository)],
    document_repository: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> SendMessagePipeline:
    return build_pipeline(
        document_vector_repository=document_vector_repository,
        document_repository=document_repository,
    )


def get_chat_service(
    send_message_pipeline: Annotated[SendMessagePipeline, Depends(get_send_message_pipeline)],
) -> ChatService:
    return ChatService(send_message_pipeline)


async def validate_api_key(
    api_key: Annotated[str, Depends(validate)]
) -> str:
    """Dependency для валидации API ключа."""
    return api_key