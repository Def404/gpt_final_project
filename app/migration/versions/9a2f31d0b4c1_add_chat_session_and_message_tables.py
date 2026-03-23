"""add chat session and message tables

Revision ID: 9a2f31d0b4c1
Revises: 43537e827107
Create Date: 2026-03-23 11:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9a2f31d0b4c1"
down_revision: Union[str, Sequence[str], None] = "43537e827107"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS chat")

    op.create_table(
        "chat_sessions",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("title", sa.TEXT(), nullable=False),
        sa.Column("is_active_in_bot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_delete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("chat_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("uid"),
        schema="chat",
    )

    op.create_table(
        "messages",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("chat_uid", sa.Uuid(), nullable=False),
        sa.Column("reply_uid", sa.Uuid(), nullable=True),
        sa.Column("sender", sa.TEXT(), nullable=False),
        sa.Column("message_text", sa.TEXT(), nullable=False),
        sa.Column("message_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.TEXT(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_uid"], ["chat.chat_sessions.uid"]),
        sa.ForeignKeyConstraint(["reply_uid"], ["chat.messages.uid"]),
        sa.PrimaryKeyConstraint("uid"),
        schema="chat",
    )


def downgrade() -> None:
    op.drop_table("messages", schema="chat")
    op.drop_table("chat_sessions", schema="chat")
    op.execute("DROP SCHEMA IF EXISTS chat")
