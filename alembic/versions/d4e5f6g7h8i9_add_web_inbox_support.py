"""add_web_inbox_support

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2025-12-21 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add web inbox support columns to players and messages tables."""
    # Add communication_mode to players (immersive or web_only)
    op.add_column(
        "players",
        sa.Column("communication_mode", sa.Text(), server_default="immersive", nullable=False),
    )

    # Add content columns to messages for web_only mode
    op.add_column("messages", sa.Column("subject", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("content", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("html_content", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("sender_name", sa.Text(), nullable=True))

    # Add index for session-based message grouping (conversation threading)
    op.create_index("idx_messages_session", "messages", ["session_id"], unique=False)


def downgrade() -> None:
    """Remove web inbox support columns."""
    op.drop_index("idx_messages_session", table_name="messages")
    op.drop_column("messages", "sender_name")
    op.drop_column("messages", "html_content")
    op.drop_column("messages", "content")
    op.drop_column("messages", "subject")
    op.drop_column("players", "communication_mode")
