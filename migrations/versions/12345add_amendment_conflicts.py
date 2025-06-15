"""add amendment conflicts table

Revision ID: 12345add
Revises: ea3a1b2c3d45
Create Date: 2025-06-15 02:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '12345add'
down_revision = 'ea3a1b2c3d45'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'amendment_conflicts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id')),
        sa.Column('amendment_a_id', sa.Integer(), sa.ForeignKey('amendments.id')),
        sa.Column('amendment_b_id', sa.Integer(), sa.ForeignKey('amendments.id')),
    )


def downgrade():
    op.drop_table('amendment_conflicts')
