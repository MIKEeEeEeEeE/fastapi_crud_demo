"""Create initial tables

Revision ID: b5ca343d986a
Revises: 7b0978dcf4c7
Create Date: 2025-08-27 01:33:40.968418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5ca343d986a'
down_revision: Union[str, None] = '7b0978dcf4c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
