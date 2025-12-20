"""replace_telegram_with_phone

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-20 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace Telegram fields with phone fields."""
    # Add new phone columns
    op.add_column('players', sa.Column('phone', sa.Text(), nullable=True))
    op.add_column('players', sa.Column('phone_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.create_unique_constraint('uq_players_phone', 'players', ['phone'])

    # Remove Telegram columns
    op.drop_constraint('players_telegram_id_key', 'players', type_='unique')
    op.drop_column('players', 'telegram_id')
    op.drop_column('players', 'telegram_username')
    op.drop_column('players', 'telegram_verified')

    # Update messages channel enum - change 'telegram' to 'sms' in existing data
    op.execute("UPDATE messages SET channel = 'sms' WHERE channel = 'telegram'")


def downgrade() -> None:
    """Restore Telegram fields from phone fields."""
    # Add Telegram columns back
    op.add_column('players', sa.Column('telegram_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('players', sa.Column('telegram_username', sa.Text(), nullable=True))
    op.add_column('players', sa.Column('telegram_id', sa.BigInteger(), nullable=True))
    op.create_unique_constraint('players_telegram_id_key', 'players', ['telegram_id'])

    # Remove phone columns
    op.drop_constraint('uq_players_phone', 'players', type_='unique')
    op.drop_column('players', 'phone_verified')
    op.drop_column('players', 'phone')

    # Revert messages channel
    op.execute("UPDATE messages SET channel = 'telegram' WHERE channel = 'sms'")
