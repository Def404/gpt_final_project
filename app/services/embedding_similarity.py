import time

from app.config_logging import get_logger
from app.schemas.similarity import SimilarityResponse, SimilarityResult
from app.services.openai_embedding import OpenAIEmbeddingService


logger = get_logger(__name__)

class EmbeddingSimilarityService:
    """Сервис поиска похожих документов по embedding-вектору."""

    def __init__(self, embedding_service: OpenAIEmbeddingService):
        self.embedding_service = embedding_service

    async def cosine_similarity(
        self,
        query: str,
        document_vector_repository,
        document_repository,
        similarity_repository,
    ) -> SimilarityResponse:
        if not query:
            logger.warning("cosine_similarity request rejected: empty query")
            raise ValueError("Query is required")

        logger.info("cosine_similarity request started", extra={"query_length": len(query)})
        start_time = time.perf_counter()
        try:
            embedding_response = await self.embedding_service.embed_text(query)
            logger.debug(
                "embedding generated",
                extra={"model": embedding_response.model, "tokens": embedding_response.usage.total_tokens},
            )

            search_results = await document_vector_repository.cosine_similarity_document_by_vector(
                embedding_response.data[0].embedding
            )
            logger.debug("vector search completed", extra={"results_count": len(search_results)})

            results: list[SimilarityResult] = []
            for document_vector, distance in search_results:
                document = await document_repository.get_by_uid(document_vector.document_uid)
                if not document:
                    logger.debug("document not found, skipping", extra={"document_uid": str(document_vector.document_uid)})
                    continue

                results.append(
                    SimilarityResult(
                        file_name=document.file_name,
                        file_link=document.file_link,
                        content=document_vector.content,
                        score=distance,
                    )
                )

            execution_time = time.perf_counter() - start_time
            logger.info(
                "cosine_similarity request completed",
                extra={
                    "execution_time": execution_time,
                    "count_results": len(results),
                    "model": embedding_response.model,
                    "total_tokens": embedding_response.usage.total_tokens,
                },
            )

            response = SimilarityResponse(
                query=query,
                generated_query=query,
                model=embedding_response.model,
                prompt_tokens=embedding_response.usage.prompt_tokens,
                completion_tokens=embedding_response.usage.total_tokens - embedding_response.usage.prompt_tokens,
                total_tokens=embedding_response.usage.total_tokens,
                count_results=len(results),
                execution_time=execution_time,
                results=results,
            )

            try:
                await similarity_repository.create(response)
                logger.debug("similarity response saved to database")
            except Exception as exc:
                logger.warning(
                    "failed to save similarity response to database",
                    extra={"error": str(exc)},
                    exc_info=True,
                )

            return response
        except Exception:
            execution_time = time.perf_counter() - start_time
            logger.error(
                "cosine_similarity request failed",
                extra={"execution_time": execution_time},
                exc_info=True,
            )
            raise