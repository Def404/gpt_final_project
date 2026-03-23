from openai import OpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse

from app.config import settings
from app.config_logging import get_logger


logger = get_logger(__name__)


class OpenAIEmbeddingService:
    """Сервис для работы с OpenAI API."""

    api_key: str = settings.EMBEDDING_API_KEY
    base_url: str = settings.EMBEDDING_BASE_URL
    model_name: str = settings.EMBEDDING_MODEL_NAME

    def __init__(self):
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.debug("OpenAIEmbeddingService initialized", extra={"model": self.model_name, "base_url": self.base_url})


    async def embed_text(self, text: str) -> CreateEmbeddingResponse:
        """Генерация вектора для текста."""

        if not text:
            logger.error("embed_text called with empty text")
            raise ValueError("Text is required")

        logger.debug("generating embedding", extra={"text_length": len(text), "model": self.model_name})
        try:
            response = self.client.embeddings.create(input=text, model=self.model_name)
            logger.info("embedding generated successfully", extra={
                "model": response.model,
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens
            })
            return response
        except Exception as e:
            logger.error("embedding generation failed", extra={"error": str(e), "model": self.model_name}, exc_info=True)
            raise ValueError(f"Error embedding text: {e}")



