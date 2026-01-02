from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AsyncDbDep
from app.core.logger import logger
from app.core.settings import settings
from app.ml.embeddings import embed_query

router = APIRouter()


@router.get(
    "/search",
    summary="Semantic search over posts using pgvector",
)
async def semantic_search(
    q: str = Query(..., min_length=1, description="User query text"),
    db: AsyncDbDep = Depends(),
    vertical: Optional[str] = Query(
        None,
        description="Optional vertical filter. Defaults to settings.vertical if omitted.",
    ),
    category: Optional[str] = Query(
        None,
        description="Optional category filter.",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of results to return.",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Offset for pagination.",
    ),
    min_score: float = Query(
        0.6,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score (0–1).",
    ),
) -> Dict[str, Any]:
    """
    Semantic search endpoint backed by pgvector.

    - Transforma `q` en un embedding (384-dim).
    - Usa `embedding <=> :query_vec` (cosine distance) para ordenar.
    - Aplica filtros opcionales (`vertical`, `category`).
    - Filtra resultados por `min_score` (cosine similarity).
    """

    if not q.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")

    # Filtro vertical: por defecto el de settings
    vertical_filter = vertical or settings.vertical

    try:
        query_vec: List[float] = embed_query(q)
    except HTTPException as exc:
        # Propagamos errores de embedding (400/500) tal cual
        logger.error(f"Embedding error for query '{q}': {exc.detail}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error generating embedding for query '{q}'")
        raise HTTPException(status_code=500, detail="Error generating query embedding") from e

    # Construimos SQL para pgvector
    #  - 1 - (embedding <=> :query_vec) = cosine similarity en [0,1]
    #  - min_score aplica como filtro duro de calidad
    sql = text(
        """
        SELECT
            pid,
            title,
            body,
            vertical,
            category,
            confidence,
            1 - (embedding <=> :query_vec) AS score
        FROM posts_sqlmodel
        WHERE embedding IS NOT NULL
          AND (:vertical IS NULL OR vertical = :vertical)
          AND (:category IS NULL OR category = :category)
          AND (1 - (embedding <=> :query_vec)) >= :min_score
        ORDER BY embedding <=> :query_vec
        LIMIT :limit
        OFFSET :offset
        """
    )

    params = {
        "query_vec": query_vec,
        "vertical": vertical_filter,
        "category": category,
        "min_score": float(min_score),
        "limit": int(limit),
        "offset": int(offset),
    }

    session: AsyncSession = db  # solo para type hints

    try:
        result = await session.execute(sql, params)
        rows = result.mappings().all()
    except Exception as e:
        logger.exception("Error executing semantic search SQL")
        raise HTTPException(status_code=500, detail="Search query failed") from e

    items: List[Dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "pid": row["pid"],
                "title": row["title"],
                "body": row["body"],
                "vertical": row["vertical"],
                "category": row["category"],
                "confidence": row["confidence"],
                "score": float(row["score"]) if row["score"] is not None else None,
            }
        )

    return {
        "status": "ok",
        "query": q,
        "vertical": vertical_filter,
        "count": len(items),
        "items": items,
    }
