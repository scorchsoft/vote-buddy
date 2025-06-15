"""add motions table and motion options

Revision ID: ea3a1b2c3d45
Revises: ccd9d99d0db0
Create Date: 2025-06-15 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'ea3a1b2c3d45'
down_revision = 'ccd9d99d0db0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'motions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id')),
        sa.Column('title', sa.String(length=255)),
        sa.Column('text_md', sa.Text()),
        sa.Column('category', sa.String(length=20)),
        sa.Column('threshold', sa.String(length=20)),
        sa.Column('ordering', sa.Integer()),
    )
    op.create_table(
        'motion_options',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('motion_id', sa.Integer(), sa.ForeignKey('motions.id')),
        sa.Column('text', sa.String(length=255)),
    )
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('motion_md')
    with op.batch_alter_table('amendments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('motion_id', sa.Integer()))
        batch_op.create_foreign_key(
            'fk_amendments_motion_id_motions',
            'motions',
            ['motion_id'],
            ['id'],
        )
    with op.batch_alter_table('votes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('motion_id', sa.Integer(), nullable=True))
        batch_op.drop_column('motion')
        batch_op.create_foreign_key('fk_votes_motion_id_motions', 'motions', ['motion_id'], ['id'])


def downgrade():
    with op.batch_alter_table('votes', schema=None) as batch_op:
        batch_op.drop_constraint('fk_votes_motion_id_motions', type_='foreignkey')
        batch_op.add_column(sa.Column('motion', sa.Boolean(), nullable=True))
        batch_op.drop_column('motion_id')
    with op.batch_alter_table('amendments', schema=None) as batch_op:
        batch_op.drop_column('motion_id')
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('motion_md', sa.Text(), nullable=True))
    op.drop_table('motion_options')
    op.drop_table('motions')
