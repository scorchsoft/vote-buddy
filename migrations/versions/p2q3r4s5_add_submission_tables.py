"""add submission tables

Revision ID: p2q3r4s5
Revises: p1q2r3s4
Create Date: 2025-06-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'p2q3r4s5'
down_revision = 'p1q2r3s4'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'motion_submissions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id')),
        sa.Column('name', sa.String(length=255)),
        sa.Column('email', sa.String(length=255)),
        sa.Column('title', sa.String(length=255)),
        sa.Column('text_md', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'amendment_submissions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('motion_id', sa.Integer(), sa.ForeignKey('motions.id')),
        sa.Column('name', sa.String(length=255)),
        sa.Column('email', sa.String(length=255)),
        sa.Column('text_md', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

def downgrade():
    op.drop_table('amendment_submissions')
    op.drop_table('motion_submissions')
