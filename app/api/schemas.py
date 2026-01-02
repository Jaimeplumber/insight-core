from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel
from pydantic import ConfigDict

# =========================================================
# BASE
# =========================================================

class PostBase(BaseModel):
    pid: str
    title: str
    body: str
    vertical: str
    category: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    n_comments: Optional[int] = None


# =========================================================
# INTERNAL (DB / PIPELINE / ADMIN)
# =========================================================

class PostInternal(PostBase):
    confidence: Optional[float] = None
    score: Optional[float] = None
    cluster_id: Optional[str] = None
    is_relevant: Optional[bool] = None
    summary: Optional[str] = None

    enriched_at: Optional[datetime] = None
    embedding_attempt_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PUBLIC API (CLIENT SAFE)
# =========================================================

class PostOut(BaseModel):
    pid: str
    title: str
    body: str
    vertical: str
    category: Optional[str]
    tags: Optional[Dict[str, str]]

    summary: Optional[str]
    score: Optional[float]
    confidence: Optional[float]
    cluster_id: Optional[str]

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# LIST / PAGINATION
# =========================================================

class PostListOut(BaseModel):
    total: int
    items: List[PostOut]
    limit: int
    offset: int
    has_more: bool
