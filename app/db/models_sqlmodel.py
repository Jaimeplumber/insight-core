from datetime import datetime
from typing import Optional, List, Dict

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func, JSON
from pgvector.sqlalchemy import Vector


class Post(SQLModel, table=True):
    __tablename__ = "posts_sqlmodel"

    # Identificador (lo provee tu ingestor, por ahora)
    pid: str = Field(primary_key=True, max_length=255)

    # Contenido principal
    title: str = Field(nullable=False)
    body: str = Field(nullable=False)

    # Para tu SaaS multi-vertical
    vertical: str = Field(nullable=False, index=True)
    category: Optional[str] = Field(default=None, max_length=100)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)

    # ----- Campos del modelo viejo que pueden ser útiles -----
    # tags -> lo guardamos como JSON (dict)
    tags: Optional[Dict[str, str]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    score: Optional[float] = None
    n_comments: Optional[int] = Field(default=0, ge=0)
    cluster_id: Optional[str] = Field(default=None, max_length=100)
    is_relevant: Optional[bool] = Field(default=None)
    summary: Optional[str] = None

    # ----- Embeddings / IA -----
    embedding: Optional[List[float]] = Field(
        sa_column=Column(Vector(384), nullable=True)
    )
    enriched_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    embedding_attempt_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # ----- Timestamps -----
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )
    )
    deleted_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True)
    )
