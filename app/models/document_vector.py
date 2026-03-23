from pgvector.sqlalchemy import VECTOR
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID

from database import Base, uuid_pk
from models.document import Document


class DocumentVector(Base):
    __table_args__ = {"schema": "documents"}

    uid: Mapped[uuid_pk]
    content: Mapped[str] = mapped_column(TEXT, nullable=False)
    embedding: Mapped[VECTOR(1024)] = mapped_column(VECTOR(1024), nullable=False)
    document_uid: Mapped[UUID] = mapped_column(ForeignKey   ("documents.documents.uid"), nullable=False)
    metadata_content: Mapped[dict] = mapped_column(JSONB, nullable=True)


    def __str__(self):
        return f"{self.__class__.__name__}(uid={self.uid}, document_uid={self.document_uid})"

    def __repr__(self):
        return str(self)