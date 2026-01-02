# app/db/models_clusters.py
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import DateTime, func
from pgvector.sqlalchemy import Vector


class Cluster(SQLModel, table=True):
    """Agrupa posts similares con embedding promedio y resumen semántico."""
    __tablename__ = "insights_clusters"

    # --- Identificación y metadata principal ---
    id: Optional[int] = Field(default=None, primary_key=True)
    vertical: str = Field(nullable=False, index=True)
    label: str = Field(default="Cluster", max_length=255)
    summary: Optional[str] = Field(default=None)

    # --- Información de agrupación ---
    n_posts: int = Field(default=0, ge=0)
    source_forum: Optional[str] = Field(default=None, max_length=100)
    last_post_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    # --- Vector promedio (pgvector compatible) ---
    centroid: Optional[List[float]] = Field(
        sa_column=Column(Vector(384), nullable=True)
    )

    # --- Auditoría ---
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now()
        )
    )
