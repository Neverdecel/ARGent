"""add_message_external_id

Revision ID: a1b2c3d4e5f6
Revises: 389108adeb63
Create Date: 2025-12-20 19:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '389108adeb63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add external_id column to messages table."""
    op.add_column('messages', sa.Column('external_id', sa.Text(), nullable=True))
    op.create_index('idx_messages_external_id', 'messages', ['external_id'], unique=False)


def downgrade() -> None:
    """Remove external_id column from messages table."""
    op.drop_index('idx_messages_external_id', table_name='messages')
    op.drop_column('messages', 'external_id')
