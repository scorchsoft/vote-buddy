"""add proposer and seconder columns to amendments

Revision ID: f3a0d98b5c17
Revises: ea3a1b2c3d45
Create Date: 2025-06-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3a0d98b5c17'
down_revision = 'ea3a1b2c3d45'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('amendments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('proposer_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('seconder_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_amendments_proposer', 'members', ['proposer_id'], ['id'])
        batch_op.create_foreign_key('fk_amendments_seconder', 'members', ['seconder_id'], ['id'])


def downgrade():
    with op.batch_alter_table('amendments', schema=None) as batch_op:
        batch_op.drop_constraint('fk_amendments_seconder', type_='foreignkey')
        batch_op.drop_constraint('fk_amendments_proposer', type_='foreignkey')
        batch_op.drop_column('seconder_id')
        batch_op.drop_column('proposer_id')
