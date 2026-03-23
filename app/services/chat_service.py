from uuid import UUID

from fastapi import HTTPException, status

from app.config_logging import get_logger
from app.models.chat_session import ChatSession
from app.models.message import Message


logger = get_logger(__name__)


class ChatService:
    def __init__(self, send_message_pipeline):
        self.send_message_pipeline = send_message_pipeline

    async def send_message(
        self,
        chat_uid: UUID | None,
        message_text: str,
        message_metadata: dict | None,
        chat_session_repository,
        message_repository,
    ):
        text = message_text.strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="message_text is required",
            )

        if chat_uid is None:
            chat = await chat_session_repository.add(
                ChatSession(
                    title=text,
                    chat_metadata={
                        "telegram_message_thread_id": (
                            message_metadata.get("telegram_message_thread_id")
                            if message_metadata
                            else None
                        )
                    },
                )
            )
        else:
            chat = await chat_session_repository.get_by_uid(chat_uid)
            if chat is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"chat with uid {chat_uid} not found",
                )

        # Keep the last 6 messages like in the C# logic (history comes as newest->oldest).
        history = await message_repository.get_by_chat_uid(chat.uid)
        history_last = history[-6:]
        history_messages_desc = list(reversed(history_last))

        user_message = await message_repository.add(
            Message(
                chat_uid=chat.uid,
                sender="user",
                message_text=text,
                status="done",
                message_metadata=message_metadata,
            )
        )

        from app.services.send_message_pipeline import PipelineContext

        context = PipelineContext(
            user_message_text=text,
            history_messages=history_messages_desc,
            chat_uid=chat.uid,
            message_metadata=message_metadata,
        )

        try:
            context = await self.send_message_pipeline.run(context)
        except Exception as exc:
            logger.error(
                "failed to run send message pipeline",
                exc_info=True,
                extra={"error": str(exc)},
            )
            bot_text = "Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте еще раз."
        else:
            if not context.search_query:
                bot_text = "Привет! Чем могу помочь? Задайте вопрос по документам — я поищу ответ в базе знаний."
            else:
                bot_text = (context.answer_json or {}).get("final_answer", "").strip()
                if not bot_text:
                    bot_text = "Не удалось сформировать ответ. Попробуйте уточнить вопрос."

        bot_message = await message_repository.add(
            Message(
                chat_uid=chat.uid,
                reply_uid=user_message.uid,
                sender="bot",
                message_text=bot_text,
                status="done",
            )
        )

        return {
            "user_message": user_message,
            "bot_message": bot_message,
            "chat": chat,
        }
