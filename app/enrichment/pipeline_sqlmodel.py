# app/enrichment/pipeline_sqlmodel.py
import asyncio
from datetime import datetime, timezone
from typing import Dict
from sqlalchemy.exc import SQLAlchemyError
from asyncio import TimeoutError
from async_timeout import timeout as async_timeout
import logging

from sqlmodel import select
from app.db.database import async_session_maker
from app.db.models_sqlmodel import Post
from app.ml.embedder import embed_text
from app.core.settings import settings

# -------------------------------------------------------------------
# ⚙️ Configuración general
# -------------------------------------------------------------------
ROW_TIMEOUT = 5      # segundos por fila
BATCH_TIMEOUT = 30   # segundos por lote

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# -------------------------------------------------------------------
# 🧠 Enriquecimiento de posts con embeddings reales
# -------------------------------------------------------------------
async def enrich_pending_posts(limit: int = 10) -> Dict[str, int]:
    """
    Enrich posts for the current vertical (multi-tenant).
    - Usa SQLModel async
    - Embeddings reales (SentenceTransformer)
    - Control por timeout
    - Batch commit
    - Idempotente (solo posts sin enriched_at)
    """
    processed = 0

    async with async_session_maker() as session:
        try:
            # --------------------------------------------------------
            # 1️⃣ Selecciona posts pendientes de enriquecer
            # --------------------------------------------------------
            stmt = (
                select(Post)
                .where(
                    Post.vertical == settings.vertical,
                    Post.enriched_at.is_(None)
                )
                .order_by(Post.pid.asc())
                .limit(limit)
            )

            async with async_timeout(BATCH_TIMEOUT):
                result = await session.execute(stmt)
                posts = result.scalars().all()

            if not posts:
                logger.info("No hay posts pendientes para %s", settings.vertical)
                return {"vertical": settings.vertical, "processed": 0, "total": 0}

            logger.info("Procesando %s posts para vertical '%s'", len(posts), settings.vertical)

            # --------------------------------------------------------
            # 2️⃣ Enriquecimiento fila por fila
            # --------------------------------------------------------
            for post in posts:
                try:
                    async with async_timeout(ROW_TIMEOUT):
                        text = f"{post.title or ''} {post.body or ''}".strip()
                        if not text:
                            logger.warning("Post %s vacío, omitido", post.pid)
                            continue

                        # ✅ Generar embedding real (CPU/GPU auto)
                        embedding = await asyncio.to_thread(embed_text, text)

                        # (Temporal) categoría dummy
                        category, confidence = "other", 0.5

                        post.embedding = embedding
                        post.category = category
                        post.confidence = confidence
                        post.enriched_at = datetime.now(timezone.utc)
                        post.updated_at = datetime.now(timezone.utc)

                        session.add(post)
                        processed += 1

                except TimeoutError:
                    logger.warning("Post %s excedió timeout y fue omitido", post.pid)
                    continue
                except Exception as e:
                    logger.error("Error procesando post %s: %s", post.pid, e)
                    continue

            # --------------------------------------------------------
            # 3️⃣ Commit del batch
            # --------------------------------------------------------
            await session.commit()

            logger.info(
                "✅ Enriquecidos %s/%s posts para '%s'",
                processed, len(posts), settings.vertical,
                extra={
                    "vertical": settings.vertical,
                    "processed": processed,
                    "total": len(posts),
                    "last_pid": posts[-1].pid if posts else None,
                }
            )

            return {"vertical": settings.vertical, "processed": processed, "total": len(posts)}

        except SQLAlchemyError as e:
            logger.error("Error en batch DB", exc_info=True)
            await session.rollback()
            raise

        except Exception as e:
            logger.error("Error inesperado en batch", exc_info=True)
            await session.rollback()
            raise


# -------------------------------------------------------------------
# 🚀 Ejecución directa (modo script)
# -------------------------------------------------------------------
if __name__ == "__main__":
    result = asyncio.run(enrich_pending_posts(limit=10))
    print("\nResultado final:", result)

