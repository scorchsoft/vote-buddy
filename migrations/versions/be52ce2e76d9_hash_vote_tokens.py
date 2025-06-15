"""hash existing vote tokens and expand column

Revision ID: be52ce2e76d9
Revises: fa1e1fb8c1a0
Create Date: 2025-06-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
import os
import hashlib

revision = 'be52ce2e76d9'
down_revision = 'fa1e1fb8c1a0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('vote_tokens', schema=None) as batch_op:
        batch_op.alter_column('token', type_=sa.String(length=64))

    connection = op.get_bind()
    salt = os.getenv('TOKEN_SALT', 'token-salt')
    tokens = connection.execute(sa.text('SELECT token FROM vote_tokens')).fetchall()
    for (tok,) in tokens:
        digest = hashlib.sha256(f"{tok}{salt}".encode()).hexdigest()
        connection.execute(sa.text('UPDATE vote_tokens SET token=:d WHERE token=:o'), {'d': digest, 'o': tok})


def downgrade():
    with op.batch_alter_table('vote_tokens', schema=None) as batch_op:
        batch_op.alter_column('token', type_=sa.String(length=36))
    # cannot reverse hashed data
