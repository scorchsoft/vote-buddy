"""merge admin log indexes and other heads

Revision ID: c16b6e000543
Revises: d3f37a6e1bdf, w3x4y5z6
Create Date: 2025-06-26 19:16:26.946434

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c16b6e000543'
down_revision = ('d3f37a6e1bdf', 'w3x4y5z6')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
