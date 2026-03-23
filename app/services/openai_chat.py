from openai import OpenAI

from config import settings
from config_logging import get_logger


logger = get_logger(__name__)


SYSTEM_PROMPT = (
    "You are a helpful corporate assistant. "
    "Answer clearly and briefly. "
    "If there is not enough context, say what is missing."
)


class OpenAIChatService:
    def __init__(self):
        api_key = settings.CHAT_API_KEY or settings.EMBEDDING_API_KEY
        if not api_key:
            raise ValueError("CHAT_API_KEY or EMBEDDING_API_KEY is required")

        self.client = OpenAI(
            api_key=api_key,
            base_url=settings.CHAT_BASE_URL or settings.EMBEDDING_BASE_URL,
        )
        self.model_name = settings.CHAT_MODEL_NAME

    async def build_answer(self, user_message_text: str, history_messages: list[str]) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend({"role": "user", "content": message_text} for message_text in history_messages)
        messages.append({"role": "user", "content": user_message_text})

        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
            top_p=0.9,
            max_tokens=1000,
            stream=False,
        )
        content = completion.choices[0].message.content
        if not content:
            logger.warning("empty content returned by chat model")
            return "Не удалось сформировать ответ. Попробуйте переформулировать запрос."
        return content.strip()
