"""add meeting files table

Revision ID: r3s4t5u6
Revises: q1w2e3r4
Create Date: 2025-07-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'r3s4t5u6'
down_revision = 'q1w2e3r4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'meeting_files',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id')),
        sa.Column('filename', sa.String(length=255)),
        sa.Column('title', sa.String(length=255)),
        sa.Column('description', sa.Text()),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('meeting_files')
