"""Add step_mode fields to chat table

Revision ID: f083351be8b3
Revises: f1e2d3c4b5a6
Create Date: 2026-02-22 00:00:00.000000

Adds step_context (JSON), parent_chat_id (String), and split_summary (Text)
columns to the chat table for Jaco's step-by-step response mode.
"""

from alembic import op
import sqlalchemy as sa

revision = "f083351be8b3"
down_revision = "f1e2d3c4b5a6"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("chat")}

    if "step_context" not in columns:
        op.add_column("chat", sa.Column("step_context", sa.JSON(), nullable=True))
    if "parent_chat_id" not in columns:
        op.add_column("chat", sa.Column("parent_chat_id", sa.String(), nullable=True))
    if "split_summary" not in columns:
        op.add_column("chat", sa.Column("split_summary", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("chat", "split_summary")
    op.drop_column("chat", "parent_chat_id")
    op.drop_column("chat", "step_context")
