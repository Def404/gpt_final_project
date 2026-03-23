from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import (
    get_chat_service,
    get_chat_session_repository,
    get_message_repository,
    validate_api_key,
)
from schemas.chat import MessageRequest, SendMessageResponse
from services.chat_service import ChatService


router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/messages/send", response_model=SendMessageResponse)
async def send_message(
    request: MessageRequest,
    api_key: Annotated[str, Depends(validate_api_key)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    chat_session_repository=Depends(get_chat_session_repository),
    message_repository=Depends(get_message_repository),
):
    _ = api_key
    result = await chat_service.send_message(
        chat_uid=request.chat_uid,
        message_text=request.message_text,
        message_metadata=request.message_metadata,
        chat_session_repository=chat_session_repository,
        message_repository=message_repository,
    )
    return result
