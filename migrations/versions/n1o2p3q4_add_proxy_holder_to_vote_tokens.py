"""add proxy_holder_id to vote_tokens

Revision ID: n1o2p3q4
Revises: m0n1o2p3
Create Date: 2025-06-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'n1o2p3q4'
down_revision = 'm0n1o2p3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('vote_tokens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('proxy_holder_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_vote_tokens_proxy_holder_id_members', 'members', ['proxy_holder_id'], ['id'])


def downgrade():
    with op.batch_alter_table('vote_tokens', schema=None) as batch_op:
        batch_op.drop_constraint('fk_vote_tokens_proxy_holder_id_members', type_='foreignkey')
        batch_op.drop_column('proxy_holder_id')
