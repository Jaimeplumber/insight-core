# app/enrichment/pipeline.py
import asyncio
from typing import Dict, Optional
from sqlalchemy import select, func, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from asyncio import TimeoutError, timeout as async_timeout

from app.api.deps import get_db_async  # usa tu helper existente
from app.ml.predict_filter import classify_problem
from app.core.logger import logger
from app.core.settings import settings
from app.db.models import Post

# ------------------------------------------------------------------
# Configuración general
# ------------------------------------------------------------------
BATCH_SIZE = 500
WORK_TIMEOUT = 30
ENRICH_TIMEOUT = 5

# ------------------------------------------------------------------
# Pipeline principal
# ------------------------------------------------------------------
async def run_enrichment_pipeline(limit: Optional[int] = None, db: Optional[AsyncSession] = None) -> Dict[str, int]:
    """
    Ejecuta el pipeline de enriquecimiento.
    Si no se pasa una sesión (db), crea una internamente.
    """
    if db is None:
        async for session in get_db_async():
            return await _run_enrichment_pipeline(limit, session)
    else:
        return await _run_enrichment_pipeline(limit, db)


async def _run_enrichment_pipeline(limit: Optional[int], db: AsyncSession) -> Dict[str, int]:
    processed = 0
    last_id = 0

    try:
        total_stmt = select(func.count(Post.pid)).where(
            Post.vertical == settings.vertical,
            Post.deleted_at.is_(None),
            Post.enriched_at.is_(None)
        )

        async with async_timeout(WORK_TIMEOUT):
            total = await db.scalar(total_stmt)

        if not total:
            logger.info("Nothing to enrich for vertical %s", settings.vertical)
            return {"processed": 0, "vertical": settings.vertical, "last_id": 0}

        if limit:
            total = min(total, limit)

        while processed < total:
            stmt = (
                select(Post)
                .where(
                    Post.vertical == settings.vertical,
                    Post.deleted_at.is_(None),
                    Post.enriched_at.is_(None),
                    Post.pid > last_id
                )
                .order_by(Post.pid.asc())
                .limit(min(BATCH_SIZE, total - processed))
            )

            async with async_timeout(WORK_TIMEOUT):
                result = await db.execute(stmt)
                posts = result.scalars().all()

            if not posts:
                break

            for post in posts:
                last_id = post.pid

                try:
                    async with async_timeout(ENRICH_TIMEOUT):
                        text = f"{post.title or ''} {post.body or ''}".strip()
                        category, confidence = await asyncio.to_thread(
                            classify_problem, text
                        )
                except TimeoutError:
                    logger.warning("Row %s timed out", post.pid)
                    continue
                except Exception as e:
                    logger.error("Row %s error: %s", post.pid, e)
                    continue

                await db.execute(
                    update(Post)
                    .where(Post.pid == post.pid)
                    .values(
                        category=category,
                        confidence=confidence,
                        enriched_at=func.now()
                    )
                )
                processed += 1

            await db.commit()
            logger.info("Batch OK: last_id=%s, processed=%s", last_id, processed)

        logger.info("✅ Pipeline finished: %s rows for %s", processed, settings.vertical)
        return {"processed": processed, "vertical": settings.vertical, "last_id": last_id}

    except SQLAlchemyError:
        logger.error("Pipeline DB error", exc_info=True)
        await db.rollback()
        raise

    except Exception:
        logger.error("Pipeline unexpected error", exc_info=True)
        await db.rollback()
        raise
