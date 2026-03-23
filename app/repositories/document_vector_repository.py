from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.document_vector import DocumentVector


class DocumentVectorRepository:
    """Репозиторий для работы с векторами документов в базе данных."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def cosine_similarity_document_by_vector(self, embedding: list[float], count_results: int = 5) -> list[tuple[DocumentVector, float]]:
        """
        Поиск документов по вектору с использованием cosine_distance.
        
        Возвращает топ 5 результатов в виде списка кортежей (DocumentVector, cosine_similarity).
        """
        if not embedding:
            raise ValueError("Embedding is required")
        
        # Преобразуем embedding в строку для использования в SQL
        embedding_str = "[" + ",".join(str(float(dim)) for dim in embedding) + "]"
        
        # SQL запрос с использованием cosine distance (оператор <=>)
        # Оператор <=> возвращает cosine distance (0 = идентичные, 1 = противоположные)
        query = text("""
            SELECT 
                uid,
                content,
                embedding,
                document_uid,
                metadata_content,
                created_at,
                1 - (embedding <=> CAST(:query_embedding AS vector)) as cosine_similarity 
            FROM documents.document_vectors
            ORDER BY cosine_similarity DESC
            LIMIT :search_k_results
        """)
        
        result = await self.session.execute(
            query,
            {"query_embedding": embedding_str, "search_k_results": count_results}
        )
        
        # Преобразуем результаты в список кортежей (DocumentVector, distance)
        rows = result.mappings().fetchall()
        results = []
        for row in rows:
            row_dict = dict(row)
            cosine_similarity = float(row_dict.pop("cosine_similarity"))
            document_vector = DocumentVector(**row_dict)
            results.append((document_vector, cosine_similarity))
        
        return results