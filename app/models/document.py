from sqlalchemy.dialects.postgresql import JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column

from database import Base, uuid_pk


class Document(Base):
    __table_args__ = {"schema": "documents"}

    uid: Mapped[uuid_pk]
    file_name: Mapped[str] = mapped_column(TEXT, nullable=False)
    file_hash: Mapped[str] = mapped_column(TEXT, nullable=True)
    file_path: Mapped[str] = mapped_column(TEXT, nullable=True)
    file_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)
    file_link: Mapped[str] = mapped_column(TEXT, nullable=True)

    def __str__(self):
        return f"{self.__class__.__name__}(uid={self.uid}, file_name={self.file_name})"

    def __repr__(self):
        return str(self)