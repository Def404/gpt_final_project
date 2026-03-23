import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from openai import OpenAI

from constants.llm_json_schemas import (
    ANSWER_JSON_SCHEMA,
    RESEARCH_PLAN_JSON_SCHEMA,
)
from config import settings
from config_logging import get_logger
from models.message import Message
from services.embedding_similarity import EmbeddingSimilarityService
from services.openai_embedding import OpenAIEmbeddingService


logger = get_logger(__name__)


class NullSimilarityRepository:
    async def create(self, _response):
        return None


RESEARCH_SYSTEM_PROMPT = (
    "Generate ONE short search query that will help find relevant information in the documents. "
    "Return it using the provided JSON schema."
)


ANSWER_SYSTEM_PROMPT = (
    "You are a helpful corporate assistant. Answer using only the provided document fragments. "
    "Follow the JSON schema."
)


@dataclass
class PipelineContext:
    user_message_text: str
    history_messages: list[Message]
    chat_uid: UUID | None
    message_metadata: dict | None

    search_query: str | None = None
    chunks: list[Any] | None = None  # EmbeddingSimilarityService.SimilarityResult
    answer_json: dict[str, Any] | None = None


def _extract_first_json_object(text: str) -> str:
    # Fallback extraction when model returns additional text; JSON schema response format
    # should normally be pure JSON, but we keep this robust.
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response")
    return match.group(0)


class ResearchQuestionStep:
    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name

    async def execute(self, context: PipelineContext) -> None:
        history_for_prompt: list[dict[str, str]] = []
        # In the original flow history is "descending" and then Reverse() is applied.
        for msg in reversed(context.history_messages):
            content = (msg.message_text or "").strip()
            if not content:
                continue
            role = "user" if msg.sender == "user" else "assistant"
            history_for_prompt.append({"role": role, "content": content})

        messages: list[dict[str, str]] = [{"role": "system", "content": RESEARCH_SYSTEM_PROMPT}]
        messages.extend(history_for_prompt)
        messages.append({"role": "user", "content": context.user_message_text.strip()})

        schema_obj = json.loads(RESEARCH_PLAN_JSON_SCHEMA)

        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.1,
            top_p=0.9,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "research_plan",
                    "schema": schema_obj,
                    "strict": True,
                },
            },
        )

        content = completion.choices[0].message.content or ""
        raw_json = _extract_first_json_object(content)
        parsed = json.loads(raw_json)

        search_query = str(parsed.get("search_query") or "").strip()
        context.search_query = search_query if search_query else None


class SearchStep:
    def __init__(
        self,
        embedding_similarity_service: EmbeddingSimilarityService,
        document_vector_repository,
        document_repository,
    ):
        self.embedding_similarity_service = embedding_similarity_service
        self.document_vector_repository = document_vector_repository
        self.document_repository = document_repository
        self.similarity_repository = NullSimilarityRepository()

    async def execute(self, context: PipelineContext) -> None:
        if not context.search_query:
            context.chunks = []
            return

        question = context.search_query.strip()
        if not question:
            context.chunks = []
            return

        similarity_response = await self.embedding_similarity_service.cosine_similarity(
            query=question,
            document_vector_repository=self.document_vector_repository,
            document_repository=self.document_repository,
            similarity_repository=self.similarity_repository,
        )

        # Mirror SearchStep.cs: unique by (file_name, content), keep best score, then filter >= 0.5
        unique: dict[tuple[str, str], Any] = {}
        for item in similarity_response.results:
            key = (item.file_name, item.content)
            prev = unique.get(key)
            if prev is None or item.score > prev.score:
                unique[key] = item

        context.chunks = [v for v in unique.values() if v.score >= 0.5]


class AnswerStep:
    def __init__(self, client: OpenAI, model_name: str, embedding_similarity_max_sources: int = 10):
        self.client = client
        self.model_name = model_name
        self.embedding_similarity_max_sources = embedding_similarity_max_sources

    async def execute(self, context: PipelineContext) -> None:
        if not context.search_query:
            context.answer_json = {"reasoning_summary": "", "relevant_sources": [], "final_answer": ""}
            return

        if not context.chunks:
            context.answer_json = {"reasoning_summary": "", "relevant_sources": [], "final_answer": ""}
            return

        # Only one question index exists (research always returns 1 question).
        chunks_list = context.chunks[: self.embedding_similarity_max_sources]

        chunks_content = "Фрагменты документов:\n" + "\n\n".join(
            f"[{idx + 1}] document: {c.file_name}\nurl: {c.file_link or ''}\ncontent: {c.content}"
            for idx, c in enumerate(chunks_list)
        )

        answer_user_content = (
            f"Исходный запрос пользователя: {context.user_message_text.strip()}\n\n"
            "Проанализируй все фрагменты документов из предыдущего сообщения пользователя и ответь на вопрос строго на их основе. "
            "Если в контексте есть релевантная информация (прямая, косвенная или выводимая) — сформулируй полный ответы. "
            "Шаблон отказа из системной инструкции используй только если ни один фрагмент не содержит информации по теме вопроса."
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Контекст (фрагменты документов для ответа):\n\n{chunks_content}",
            },
        ]

        if context.history_messages:
            for msg in reversed(context.history_messages):
                content = (msg.message_text or "").strip()
                if not content:
                    continue
                role = "user" if msg.sender == "user" else "assistant"
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": answer_user_content})

        schema_obj = json.loads(ANSWER_JSON_SCHEMA)
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
            top_p=0.9,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "answer",
                    "schema": schema_obj,
                    "strict": True,
                },
            },
        )

        content = completion.choices[0].message.content or ""
        raw_json = _extract_first_json_object(content)
        parsed = json.loads(raw_json)
        context.answer_json = parsed


class SendMessagePipeline:
    def __init__(self, client: OpenAI, model_name: str, document_vector_repository, document_repository):
        self.client = client
        self.model_name = model_name
        self.embedding_similarity_service = EmbeddingSimilarityService(
            embedding_service=OpenAIEmbeddingService()
        )
        self.document_vector_repository = document_vector_repository
        self.document_repository = document_repository

    async def run(self, context: PipelineContext) -> PipelineContext:
        research_step = ResearchQuestionStep(self.client, self.model_name)
        await research_step.execute(context)

        search_step = SearchStep(
            embedding_similarity_service=self.embedding_similarity_service,
            document_vector_repository=self.document_vector_repository,
            document_repository=self.document_repository,
        )
        await search_step.execute(context)

        answer_step = AnswerStep(self.client, self.model_name)
        await answer_step.execute(context)

        return context


def build_pipeline(
    document_vector_repository,
    document_repository,
) -> SendMessagePipeline:
    api_key = settings.CHAT_API_KEY or settings.EMBEDDING_API_KEY
    if not api_key:
        raise ValueError("CHAT_API_KEY or EMBEDDING_API_KEY is required")

    base_url = settings.CHAT_BASE_URL or settings.EMBEDDING_BASE_URL
    if not base_url:
        raise ValueError("CHAT_BASE_URL or EMBEDDING_BASE_URL is required")

    client = OpenAI(api_key=api_key, base_url=base_url)
    return SendMessagePipeline(
        client=client,
        model_name=settings.CHAT_MODEL_NAME,
        document_vector_repository=document_vector_repository,
        document_repository=document_repository,
    )

