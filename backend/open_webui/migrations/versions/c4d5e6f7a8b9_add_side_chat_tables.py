"""Add side_chat and side_chat_message tables

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-02-22 00:00:03.000000

Creates the side_chat and side_chat_message tables for Jaco's side chat
feature, which allows branched discussions on individual steps.
"""

from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "side_chat" not in tables:
        op.create_table(
            "side_chat",
            sa.Column("id", sa.String(), primary_key=True, unique=True),
            sa.Column("chat_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("step_index", sa.Integer(), nullable=False),
            sa.Column("original_step_content", sa.Text(), nullable=False),
            sa.Column("combined_step_content", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="open"),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "side_chat_chat_id_idx",
            "side_chat",
            ["chat_id"],
        )
        op.create_index(
            "side_chat_user_id_idx",
            "side_chat",
            ["user_id"],
        )

    if "side_chat_message" not in tables:
        op.create_table(
            "side_chat_message",
            sa.Column("id", sa.String(), primary_key=True, unique=True),
            sa.Column("side_chat_id", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("ordering", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "side_chat_msg_side_chat_id_idx",
            "side_chat_message",
            ["side_chat_id"],
        )


def downgrade():
    op.drop_index("side_chat_msg_side_chat_id_idx", table_name="side_chat_message")
    op.drop_table("side_chat_message")
    op.drop_index("side_chat_user_id_idx", table_name="side_chat")
    op.drop_index("side_chat_chat_id_idx", table_name="side_chat")
    op.drop_table("side_chat")
