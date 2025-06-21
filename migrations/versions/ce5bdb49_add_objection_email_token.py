"""add email and token to amendment objections"""

revision = 'ce5bdb49'
down_revision = 'e3b1c6d7e4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('amendment_objections', sa.Column('email', sa.String(255)))
    op.add_column('amendment_objections', sa.Column('token', sa.String(36)))
    op.add_column('amendment_objections', sa.Column('confirmed_at', sa.DateTime()))


def downgrade():
    op.drop_column('amendment_objections', 'confirmed_at')
    op.drop_column('amendment_objections', 'token')
    op.drop_column('amendment_objections', 'email')
