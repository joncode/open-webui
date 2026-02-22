"""Add topic tracking fields to chat table

Revision ID: a7b8c9d0e1f2
Revises: f083351be8b3
Create Date: 2026-02-22 00:00:01.000000

Adds topic_embedding (JSON) and message_embeddings (JSON) columns
to the chat table for Jaco's auto-topic-split feature.
"""

from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f083351be8b3"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("chat")}

    if "topic_embedding" not in columns:
        op.add_column("chat", sa.Column("topic_embedding", sa.JSON(), nullable=True))
    if "message_embeddings" not in columns:
        op.add_column(
            "chat", sa.Column("message_embeddings", sa.JSON(), nullable=True)
        )


def downgrade():
    op.drop_column("chat", "message_embeddings")
    op.drop_column("chat", "topic_embedding")
