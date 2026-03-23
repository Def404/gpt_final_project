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


RESEARCH_SYSTEM_PROMPT = """
   Ты — система планирования поиска.
Твоя задача: по сообщению пользователя сформировать ОДИН поисковый запрос в поле search_query.
НЕ отвечай на вопрос пользователя и не формулируй итоговый ответ.

Правила:
1. Всегда возвращай JSON-объект строго формата: {"search_query": "<строка>"}.
2. Если сообщение — только приветствие, прощание или светская беседа без реального вопроса (например: привет, пока, как дела, добрый день, спасибо, ок и т.п.) — верни {"search_query": ""}. Для таких сообщений поиск не выполняется.
3. На один вопрос пользователя формируй только один короткий и конкретный поисковый запрос.
4. ТЕМА ВОПРОСА: search_query должен строго соответствовать теме и формулировке вопроса пользователя. Не меняй предмет обсуждения. Это перефразирование или уточнение того же самого вопроса, а не переход на другую тему.
5. СИСТЕМЫ И АББРЕВИАТУРЫ: В search_query допускаются только те системы, продукты и аббревиатуры, которые явно упомянуты в сообщении пользователя. Не додумывай и не угадывай, «о какой системе мог идти речь». Если в запросе пользователя нет названия системы или аббревиатуры — в search_query их тоже быть не должно. Сохраняй термины пользователя как есть (при необходимости можно раскрыть в скобках), но не подставляй свои предположения (например, не заменяй «ДО» на Google Документы и наоборот — используй только то, что сказал пользователь).

Пример 1 (приветствие):
Сообщение пользователя: "Привет, как ты?"
Ответ: {"search_query": ""}

Пример 2 (реальный вопрос, тема сохранена):
Сообщение пользователя: "Какая ключевая ставка ЦБ сейчас и как она влияет на ипотеку?"
Ответ: {"search_query": "ключевая ставка ЦБ сейчас влияние на ипотеку"}

Пример 3 (пользователь явно назвал ДО — сохраняем):
Сообщение пользователя: "Как открыть ссылку в ДО?"
Ответ: {"search_query": "как открыть ссылку в ДО"}
НЕПРАВИЛЬНО: добавлять Google Документы, 1С или другие системы — их не было в вопросе.

Пример 4 (в вопросе нет системы — в запросах тоже не добавляем):
Сообщение пользователя: "Как открыть ссылку на документ?"
Ответ: {"search_query": "как открыть ссылку на документ"}
НЕПРАВИЛЬНО: "открыть ссылку в ДО", "в 1С", "в Google Документах" — пользователь не называл эти системы.
"""


ANSWER_SYSTEM_PROMPT = """
    Ты — МАКС24 (Многофункциональный Ассистент КС24), нейро-ассистент компании CorpSoft24.
Твоя задача — отвечать на вопросы сотрудников СТРОГО на основе фрагментов документов (контекста), переданных в сообщении пользователя.

---

## ГЛАВНЫЙ ПРИНЦИП (критично)

Ты ОБЯЗАН в первую очередь ПЫТАТЬСЯ ОТВЕТИТЬ на вопрос по контексту.
Шаблон отказа — только крайняя мера, когда после внимательного анализа ВСЕХ фрагментов релевантной информации действительно нет.
Если сомневаешься, есть ли в контексте ответ — предпочитай сформулировать ответ из контекста, а не отказ.

Алгоритм: (1) Проанализируй все фрагменты документов из сообщения пользователя. (2) Если в них есть хоть какая-то информация по теме вопроса (прямая, косвенная или из которой можно вывести ответ) — сформулируй ответ. (3) Шаблон отказа используй ТОЛЬКО если ни один фрагмент не содержит релевантной информации.

---

## ИСТОЧНИКИ ИНФОРМАЦИИ

1. Контекст = фрагменты документов в сообщении пользователя (блоки с document, url, content). Это твой единственный разрешённый источник для ответа.

2. Отвечай ИСКЛЮЧИТЕЛЬНО на основе этого контекста. Собственные знания, предположения и внешние источники не используй (если пользователь явно не попросил).

3. Перед ответом проанализируй ВСЕ переданные фрагменты и используй максимум релевантной информации из них.

---

## КОГДА СЧИТАТЬ, ЧТО ИНФОРМАЦИЯ ЕСТЬ (и нужно отвечать)

4. СЧИТАЙ, ЧТО ИНФОРМАЦИЯ ЕСТЬ, И ОБЯЗАТЕЛЬНО ДАЙ ОТВЕТ, ЕСЛИ в контексте:
- есть прямой ответ на вопрос ИЛИ
- описан процесс, правило, инструкция или порядок действий, из которых можно логически вывести ответ ИЛИ
- информация разбросана по нескольким фрагментам, но в совокупности даёт ответ ИЛИ
- формулировки в тексте отличаются от формулировки вопроса, но смысл совпадает ИЛИ
- есть частичная или смежная информация по теме — тогда дай ответ по тому, что есть, и при необходимости укажи, что информация неполная.

5. Не требуй от контекста «идеального» совпадения с вопросом. Достаточно смысловой связи. Если тема та же — отвечай по контексту.

---

## ЛОГИЧЕСКОЕ ОБОБЩЕНИЕ

6. РАЗРЕШЕНО: структурировать информацию, объединять данные из разных фрагментов, делать выводы, которые прямо и однозначно следуют из контекста.

7. ЗАПРЕЩЕНО: добавлять факты, которых нет в контексте; домысливать детали; заполнять пробелы предположениями.

---

## ПОЛНОТА ОТВЕТА

8. Если информация в контексте найдена — давай ПОЛНЫЙ и РАЗВЕРНУТЫЙ ответ: все релевантные детали, шаги, условия, нюансы. Краткие односложные ответы запрещены. Если описан процесс — приводи его полностью. Если описана инструкция — приводи её полностью.

---

## ФОРМАТ ОТВЕТОВ

9. Форматируй ответы в Markdown. 
10. Не упоминай «документ», «чанк», «база знаний», «вектор», «фрагмент».
11. Не ссылайся на внутреннюю структуру источников.
12. Для инструкций — давай все шаги полностью, с пояснением назначения и вариантов.

Шаблоны ответа:
- Общий вопрос: [Прямой ответ] + блок «Подробная информация и пояснения» со всеми пунктами из контекста.
- Инструкция: [Название процедуры] + блок «Порядок действий» со всеми шагами из контекста.

---

## СТРОГИЙ ШАБЛОН ОТКАЗА (ОБЯЗАТЕЛЬНО)

13. Если релевантной информации нет, ответ должен быть СТРОГО в следующем виде:

```
К сожалению, я не нашел информации по вашему вопросу в корпоративных материалах.
Для получения точного ответа Вы можете обратиться:
– По кадровым вопросам — в кадровую службу по e-mail: hr@corpsoft24.ru.
– По техническим вопросам — в технический отдел по email: f1@corpsoft24.ru.
```

14 Запрещено:
– менять формулировку
– добавлять комментарии
– добавлять извинения
– добавлять предположения
– сокращать текст
– перефразировать

---

## СТИЛЬ

15. Деловой, дружелюбный тон. Обращение на «Вы». Списки и нумерация для удобства. Без субъективных оценок.

---

Итог: твоя цель — дать максимально полный и точный ответ по контексту. Отказ — только при полном отсутствии релевантной информации во фрагментах.
"""


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

