"""add deadlines to amendment objections

Revision ID: p1q2r3t4
Revises: o3p4q5r6
Create Date: 2025-07-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "p1q2r3t4"
down_revision = ("o3p4q5r6", "e3b1c6d7e4")
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("amendment_objections", schema=None) as batch_op:
        batch_op.add_column(sa.Column("deadline_first", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("deadline_final", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("amendment_objections", schema=None) as batch_op:
        batch_op.drop_column("deadline_final")
        batch_op.drop_column("deadline_first")

