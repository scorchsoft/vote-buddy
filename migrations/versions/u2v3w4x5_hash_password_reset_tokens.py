"""hash password reset tokens and extend column"""

revision = 'u2v3w4x5'
down_revision = 't1u2v3w4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
import os
import hashlib


def upgrade():
    connection = op.get_bind()
    if not connection.dialect.has_table(connection, 'password_reset_tokens'):
        op.create_table(
            'password_reset_tokens',
            sa.Column('token', sa.String(length=64), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), index=True),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('used_at', sa.DateTime()),
        )
        return

    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.alter_column('token', type_=sa.String(length=64))

    salt = os.getenv('TOKEN_SALT', 'token-salt')
    tokens = connection.execute(sa.text('SELECT token FROM password_reset_tokens')).fetchall()
    for (tok,) in tokens:
        digest = hashlib.sha256(f"{tok}{salt}".encode()).hexdigest()
        connection.execute(sa.text('UPDATE password_reset_tokens SET token=:d WHERE token=:o'), {'d': digest, 'o': tok})


def downgrade():
    connection = op.get_bind()
    if connection.dialect.has_table(connection, 'password_reset_tokens'):
        with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
            batch_op.alter_column('token', type_=sa.String(length=36))
    # cannot reverse hashed data
