"""add results doc publish flag and intro

Revision ID: l7m8n9o0p1
Revises: k1l2m3n4o5p6
Create Date: 2025-07-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'l7m8n9o0p1'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('results_doc_published', sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column('results_doc_intro_md', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('results_doc_intro_md')
        batch_op.drop_column('results_doc_published')
