from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Header, HTTPException
from sqlalchemy import func, select, or_, update, text
from sqlalchemy.exc import SQLAlchemyError
from asyncio import TimeoutError, timeout as async_timeout

from app.api.deps import AsyncDbDep
from app.db.models_sqlmodel import Post  # ← único modelo
from app.api.schemas import (
    PostOut,
    PostListOut,
    PostCreateIn,
    PostUpdateIn,
)
from app.core.logger import logger
from app.core.settings import settings
from app.ml.embeddings import cached_embed_query

router = APIRouter()

COUNT_TIMEOUT = 1
POSTS_TIMEOUT = 5


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def build_base_filters(
    q: Optional[str] = None,
    cluster_id: Optional[str] = None,
):
    filters = [
        Post.vertical == settings.vertical,
        Post.deleted_at.is_(None),
    ]

    if q:
        filters.append(
            or_(
                Post.title.ilike(f"%{q}%"),
                Post.body.ilike(f"%{q}%"),
            )
        )

    if cluster_id:
        filters.append(Post.cluster_id == cluster_id)

    return filters


# ---------------------------------------------------------
# GET /posts (público)
# ---------------------------------------------------------
@router.get("/posts", response_model=PostListOut)
async def read_posts(
    db: AsyncDbDep,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    after: Optional[datetime] = Query(
        None, description="ISO 8601 UTC cursor para paginación hacia atrás"
    ),
    cluster_id: Optional[str] = Query(
        None, description="Filtrar por cluster_id"
    ),
):
    filters = build_base_filters(cluster_id=cluster_id)

    if after:
        filters.append(Post.created_at < after)

    # -------------------------
    # Count
    # -------------------------
    try:
        async with async_timeout(COUNT_TIMEOUT):
            total = await db.scalar(
                select(func.count(Post.pid)).where(*filters)
            )
    except TimeoutError:
        logger.error("Count timeout", exc_info=True)
        raise HTTPException(status_code=504, detail="Count timeout")

    # -------------------------
    # Query
    # -------------------------
    try:
        async with async_timeout(POSTS_TIMEOUT):
            result = await db.scalars(
                select(Post)
                .where(*filters)
                .order_by(Post.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            posts = result.all()
    except TimeoutError:
        logger.error("Select timeout", exc_info=True)
        raise HTTPException(status_code=504, detail="Select timeout")
    except SQLAlchemyError:
        logger.error("DB error on read_posts", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")

    return PostListOut(
        total=total or 0,
        items=[PostOut.from_orm(p) for p in posts],
        limit=limit,
        offset=offset,
        has_more=len(posts) == limit,
    )


# ---------------------------------------------------------
# GET /posts/search (texto plano, público)
# ---------------------------------------------------------
@router.get("/posts/search", response_model=PostListOut)
async def search_posts(
    db: AsyncDbDep,
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    cluster_id: Optional[str] = Query(
        None, description="Filtrar por cluster_id"
    ),
):
    filters = build_base_filters(q=q, cluster_id=cluster_id)

    # -------------------------
    # Count
    # -------------------------
    try:
        async with async_timeout(COUNT_TIMEOUT):
            total = await db.scalar(
                select(func.count(Post.pid)).where(*filters)
            )
    except TimeoutError:
        logger.error("Count timeout in search", exc_info=True)
        raise HTTPException(status_code=504, detail="Count timeout")

    # -------------------------
    # Query
    # -------------------------
    try:
        async with async_timeout(POSTS_TIMEOUT):
            result = await db.scalars(
                select(Post)
                .where(*filters)
                .order_by(Post.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            posts = result.all()
    except TimeoutError:
        logger.error("Select timeout in search", exc_info=True)
        raise HTTPException(status_code=504, detail="Select timeout")
    except SQLAlchemyError:
        logger.error("DB error in search", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")

    return PostListOut(
        total=total or 0,
        items=[PostOut.from_orm(p) for p in posts],
        limit=limit,
        offset=offset,
        has_more=len(posts) == limit,
    )


# ---------------------------------------------------------
# POST /posts (interno)
# ---------------------------------------------------------
@router.post("/posts", response_model=PostOut, include_in_schema=False)
async def create_post(
    post_in: PostCreateIn,
    db: AsyncDbDep,
    x_internal_key: str = Header(..., alias="X-Internal-Key"),
):
    if x_internal_key != settings.internal_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        post = Post(**post_in.dict(), vertical=settings.vertical)
        db.add(post)
        await db.commit()
        await db.refresh(post)
        return PostOut.from_orm(post)
    except SQLAlchemyError:
        logger.error("DB error creating post", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


# ---------------------------------------------------------
# PATCH /posts/{pid} (interno)
# ---------------------------------------------------------
@router.patch("/posts/{pid}", response_model=PostOut, include_in_schema=False)
async def update_post(
    pid: str,
    post_in: PostUpdateIn,
    db: AsyncDbDep,
    x_internal_key: str = Header(..., alias="X-Internal-Key"),
):
    if x_internal_key != settings.internal_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        stmt = (
            update(Post)
            .where(Post.pid == pid, Post.vertical == settings.vertical)
            .values(**post_in.dict(exclude_unset=True), updated_at=func.now())
            .execution_options(synchronize_session="fetch")
        )
        result = await db.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Post not found")

        await db.commit()
        post = await db.get(Post, pid)
        return PostOut.from_orm(post)
    except SQLAlchemyError:
        logger.error("DB error updating post", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


# ---------------------------------------------------------
# DELETE /posts/{pid} (soft-delete, interno)
# ---------------------------------------------------------
@router.delete("/posts/{pid}", status_code=204, include_in_schema=False)
async def delete_post(
    pid: str,
    db: AsyncDbDep,
    x_internal_key: str = Header(..., alias="X-Internal-Key"),
):
    if x_internal_key != settings.internal_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        stmt = (
            update(Post)
            .where(Post.pid == pid, Post.vertical == settings.vertical)
            .values(deleted_at=func.now())
            .execution_options(synchronize_session="fetch")
        )
        result = await db.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Post not found")

        await db.commit()
    except SQLAlchemyError:
        logger.error("DB error deleting post", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")


# ---------------------------------------------------------
# GET /posts/semantic-search (pgvector)
# ---------------------------------------------------------
@router.get("/posts/semantic-search", response_model=PostListOut)
async def semantic_search_posts(
    db: AsyncDbDep,
    q: str = Query(..., min_length=2, max_length=200),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    try:
        query_vec = cached_embed_query(q).tolist()
    except Exception as e:
        logger.error(f"Embedding failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Embedding failed")

    sql = """
        SELECT
            pid,
            title,
            body,
            vertical,
            category,
            confidence,
            enriched_at,
            embedding_attempt_at,
            created_at,
            updated_at,
            deleted_at,
            1 - (embedding <=> :query_vec) AS score
        FROM posts_sqlmodel
        WHERE embedding IS NOT NULL
          AND deleted_at IS NULL
          AND vertical = :vertical
          AND (1 - (embedding <=> :query_vec)) >= :min_score
        ORDER BY score DESC
        LIMIT :limit OFFSET :offset
    """

    params = {
        "query_vec": query_vec,
        "vertical": settings.vertical,
        "min_score": float(min_score),
        "limit": limit,
        "offset": offset,
    }

    try:
        result = await db.execute(text(sql), params)
        rows = result.mappings().all()
    except SQLAlchemyError as e:
        logger.error(f"Semantic search SQL error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")

    items = [
        PostOut(
            pid=row["pid"],
            title=row["title"],
            body=row["body"],
            vertical=row["vertical"],
            category=row.get("category"),
            tags=None,
            summary=None,
            score=row.get("score"),
            confidence=row.get("confidence"),
            cluster_id=None,
            created_at=row["created_at"],
        )
        for row in rows
    ]

    return PostListOut(
        total=len(items),
        items=items,
        limit=limit,
        offset=offset,
        has_more=len(items) == limit,
    )
