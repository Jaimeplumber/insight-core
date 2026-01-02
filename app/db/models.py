from sqlalchemy import Column, String, Text, Integer, Float, DateTime
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

class Post(Base):
    __tablename__ = "posts"

    pid = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    tags = Column(Text)  # en SQLite, guardar como JSON o CSV
    score = Column(Float)
    n_comments = Column(Integer)
    vertical = Column(String(100), index=True)
    cluster_id = Column(String(100))
    is_relevant = Column(Integer)
    summary = Column(Text)

    category = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    enriched_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)