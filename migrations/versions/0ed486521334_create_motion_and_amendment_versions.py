"""create motion and amendment versions

Revision ID: 0ed486521334
Revises: ab01cd23ef45
Create Date: 2025-06-23 21:22:53.992407

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ed486521334'
down_revision = 'ab01cd23ef45'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'motion_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('motion_id', sa.Integer(), sa.ForeignKey('motions.id'), index=True),
        sa.Column('title', sa.String(length=255)),
        sa.Column('text_md', sa.Text()),
        sa.Column('final_text_md', sa.Text()),
        sa.Column('proposer_id', sa.Integer()),
        sa.Column('seconder_id', sa.Integer()),
        sa.Column('board_proposed', sa.Boolean()),
        sa.Column('board_seconded', sa.Boolean()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_table(
        'amendment_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('amendment_id', sa.Integer(), sa.ForeignKey('amendments.id'), index=True),
        sa.Column('text_md', sa.Text()),
        sa.Column('proposer_id', sa.Integer()),
        sa.Column('seconder_id', sa.Integer()),
        sa.Column('board_proposed', sa.Boolean()),
        sa.Column('board_seconded', sa.Boolean()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade():
    op.drop_table('amendment_versions')
    op.drop_table('motion_versions')
