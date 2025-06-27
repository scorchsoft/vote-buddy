"""increase_app_settings_value_column_size

Revision ID: 868e8e5a5b92
Revises: fcfb45c0555d
Create Date: 2025-06-27 17:53:19.582693

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '868e8e5a5b92'
down_revision = 'fcfb45c0555d'
branch_labels = None
depends_on = None


def upgrade():
    # Change app_settings.value column from VARCHAR(255) to TEXT
    op.alter_column('app_settings', 'value',
                    existing_type=sa.String(255),
                    type_=sa.Text(),
                    existing_nullable=True)


def downgrade():
    # Revert app_settings.value column back to VARCHAR(255)
    op.alter_column('app_settings', 'value',
                    existing_type=sa.Text(),
                    type_=sa.String(255),
                    existing_nullable=True)
