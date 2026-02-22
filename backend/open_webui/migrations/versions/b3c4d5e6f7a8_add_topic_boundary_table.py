"""Add topic_boundary table

Revision ID: b3c4d5e6f7a8
Revises: a7b8c9d0e1f2
Create Date: 2026-02-22 00:00:02.000000

Creates the topic_boundary table for Jaco's auto-topic-split feature.
Records each split event linking original and new chats.
"""

from alembic import op
import sqlalchemy as sa

revision = "b3c4d5e6f7a8"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "topic_boundary" not in tables:
        op.create_table(
            "topic_boundary",
            sa.Column("id", sa.String(), primary_key=True, unique=True),
            sa.Column("original_chat_id", sa.String(), nullable=False),
            sa.Column("new_chat_id", sa.String(), nullable=False),
            sa.Column("triggering_message", sa.Text(), nullable=False),
            sa.Column("old_topic", sa.Text(), nullable=True),
            sa.Column("new_topic", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), default=0.0),
            sa.Column("split_timestamp", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "topic_boundary_original_idx",
            "topic_boundary",
            ["original_chat_id"],
        )
        op.create_index(
            "topic_boundary_new_idx",
            "topic_boundary",
            ["new_chat_id"],
        )


def downgrade():
    op.drop_index("topic_boundary_new_idx", table_name="topic_boundary")
    op.drop_index("topic_boundary_original_idx", table_name="topic_boundary")
    op.drop_table("topic_boundary")
