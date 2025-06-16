"""add amendment merge table"""

revision = 'c1e2f3g4h5'
down_revision = '12345add'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'amendment_merges',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('combined_id', sa.Integer(), sa.ForeignKey('amendments.id')),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('amendments.id')),
    )


def downgrade():
    op.drop_table('amendment_merges')
