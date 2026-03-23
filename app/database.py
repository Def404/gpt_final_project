import re

from datetime import datetime
from typing import Annotated, AsyncGenerator
from uuid import UUID, uuid4


from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column

from app.config import get_db_url

DATABASE_URL = get_db_url()

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


uuid_pk = Annotated[UUID, mapped_column(primary_key=True, default=uuid4)]
created_at = Annotated[datetime, mapped_column(server_default=func.now())]
updated_at = Annotated[datetime, mapped_column(server_default=func.now(), onupdate=datetime.now)]

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения сессии БД в FastAPI.
    Автоматически закрывает сессию после использования.
    """
    async with async_session_maker() as db_session:
        yield db_session

class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    @staticmethod
    def _pluralize(word: str) -> str:
        if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
            return f"{word[:-1]}ies"
        if re.search(r"(s|x|z|ch|sh)$", word):
            return f"{word}es"
        return f"{word}s"

    @declared_attr.directive
    def __tablename__(cls) -> str:
        snake_case_name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return cls._pluralize(snake_case_name)

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]