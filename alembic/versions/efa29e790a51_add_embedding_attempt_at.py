"""
add embedding_attempt_at

Revision ID: efa29e790a51
Revises: 0f4aaec3786d
Create Date: 2025-11-09 19:26:44.812959
"""

from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "efa29e790a51"
down_revision: Union[str, Sequence[str], None] = "0f4aaec3786d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # --- SAFE: vector index may not exist ---
    op.execute(
        "DROP INDEX IF EXISTS idx_clusters_centroid"
    )

    # --- SAFE: constraint may not exist ---
    op.execute(
        """
        ALTER TABLE insights_clusters
        DROP CONSTRAINT IF EXISTS uq_insights_clusters_id
        """
    )


def downgrade() -> None:
    """Downgrade schema."""

    # --- Restore constraint safely ---
    op.execute(
        """
        ALTER TABLE insights_clusters
        ADD CONSTRAINT uq_insights_clusters_id UNIQUE (id)
        """
    )

    # --- Restore vector index ---
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_clusters_centroid
        ON insights_clusters
        USING ivfflat (centroid vector_cosine_ops)
        WITH (lists = 100)
        """
    )
