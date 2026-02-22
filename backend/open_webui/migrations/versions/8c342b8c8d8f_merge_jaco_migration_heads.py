"""merge jaco migration heads

Revision ID: 8c342b8c8d8f
Revises: b2c3d4e5f6a7, c4d5e6f7a8b9
Create Date: 2026-02-22 14:51:13.175069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '8c342b8c8d8f'
down_revision: Union[str, None] = ('b2c3d4e5f6a7', 'c4d5e6f7a8b9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
