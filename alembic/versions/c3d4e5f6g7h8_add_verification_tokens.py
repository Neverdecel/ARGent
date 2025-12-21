"""add_verification_tokens

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-12-21 15:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create verification_tokens table for email and phone verification."""
    op.create_table(
        "verification_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_type", sa.Text(), nullable=False),
        sa.Column("token_value", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Index for efficient token lookup (only active tokens)
    op.execute(
        """
        CREATE INDEX idx_verification_tokens_lookup
        ON verification_tokens (token_type, token_value)
        WHERE used_at IS NULL
        """
    )

    # Index for efficient expiry cleanup (only active tokens)
    op.execute(
        """
        CREATE INDEX idx_verification_tokens_expiry
        ON verification_tokens (expires_at)
        WHERE used_at IS NULL
        """
    )

    # Index for finding active tokens by player (rate limiting, invalidation)
    op.execute(
        """
        CREATE INDEX idx_verification_tokens_player
        ON verification_tokens (player_id, token_type)
        WHERE used_at IS NULL
        """
    )


def downgrade() -> None:
    """Drop verification_tokens table."""
    op.drop_index("idx_verification_tokens_player", table_name="verification_tokens")
    op.drop_index("idx_verification_tokens_expiry", table_name="verification_tokens")
    op.drop_index("idx_verification_tokens_lookup", table_name="verification_tokens")
    op.drop_table("verification_tokens")
