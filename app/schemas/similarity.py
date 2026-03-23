from typing import Optional
from pydantic import BaseModel, ConfigDict


class SimilarityRequest(BaseModel):
    query: str
    count_results: int = 5


class SimilarityResult(BaseModel):
    file_name: str
    file_link: Optional[str]
    content: str
    score: float

    model_config = ConfigDict(from_attributes=True)

class SimilarityResponse(BaseModel):
    query: str
    generated_query: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    count_results: int
    execution_time: float
    results: list[SimilarityResult]

    model_config = ConfigDict(from_attributes=True)
