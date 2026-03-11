"""agent1: lock down privacy defaults and set default model

Revision ID: 41c140e7633d
Revises: 8c342b8c8d8f
Create Date: 2026-03-11 11:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision: str = "41c140e7633d"
down_revision: Union[str, None] = "8c342b8c8d8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply Agent1 config defaults to the DB config table.

    These settings override any previously persisted values:
    - Default model: venice-uncensored
    - Disable community sharing, message ratings, prompt suggestions
    - Enable OpenAI API
    - Disable evaluation arena
    """
    conn = op.get_bind()
    row = conn.execute(sa.text("SELECT data FROM config LIMIT 1")).fetchone()

    if not row:
        # First boot — env vars will seed config, nothing to migrate
        return

    data = json.loads(row[0]) if isinstance(row[0], str) else row[0]

    # UI defaults
    data.setdefault("ui", {})
    data["ui"]["default_models"] = "venice-uncensored"
    data["ui"]["enable_community_sharing"] = False
    data["ui"]["enable_message_rating"] = False
    data["ui"]["prompt_suggestions"] = []

    # Enable OpenAI API
    data.setdefault("openai", {})
    data["openai"]["enable"] = True

    # Disable evaluation arena
    data.setdefault("evaluation", {})
    data["evaluation"].setdefault("arena", {})
    data["evaluation"]["arena"]["enable"] = False

    conn.execute(
        sa.text("UPDATE config SET data = :data"),
        {"data": json.dumps(data)},
    )


def downgrade() -> None:
    """No-op — we don't restore previous config values on downgrade."""
    pass
