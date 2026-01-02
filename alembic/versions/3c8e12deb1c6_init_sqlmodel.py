"""init sqlmodel

Revision ID: 3c8e12deb1c6
Revises:
Create Date: 2025-10-19 17:41:08.972599
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3c8e12deb1c6"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 🚫 Saltamos las operaciones que no aplican a PostgreSQL
    # (eran de una base SQLite antigua que ya no existe)
    # op.drop_index(op.f('ix_problems_id'), table_name='problems')
    # op.drop_index(op.f('ix_problems_title'), table_name='problems')
    # op.drop_table('problems')
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Solo se restaura si alguna vez se desea volver atrás.
    op.create_table(
        "problems",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("title", sa.VARCHAR(), nullable=True),
        sa.Column("description", sa.VARCHAR(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_problems_title"), "problems", ["title"], unique=False)
    op.create_index(op.f("ix_problems_id"), "problems", ["id"], unique=False)
