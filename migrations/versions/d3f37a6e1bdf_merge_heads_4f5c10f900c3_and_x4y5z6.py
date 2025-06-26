"""merge heads 4f5c10f900c3 and x4y5z6

Revision ID: d3f37a6e1bdf
Revises: 4f5c10f900c3, x4y5z6
Create Date: 2025-06-26 09:02:10.519636

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3f37a6e1bdf'
down_revision = ('4f5c10f900c3', 'x4y5z6')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
