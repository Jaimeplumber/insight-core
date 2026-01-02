import asyncio
import numpy as np
import signal
import sys
import os
import atexit
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from datetime import datetime, timedelta
from typing import List, Union, Callable
from contextlib import nullcontext

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.future import select
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential

from app.db.database import async_session_maker
from app.db.models_sqlmodel import Post
from app.core.logger import logger
from app.core.settings import settings


# ============================================================
# ⚙️ Optional Prometheus Metrics
# ============================================================
try:
    from prometheus_client import Counter, Histogram
    USE_PROM = True
    emb_ok = Counter("embeddings_generated_total", "Embeddings exitosos")
    emb_fail = Counter("embeddings_failed_total", "Embeddings fallidos")
    emb_dur = Histogram("embedding_batch_duration_seconds", "Duración del batch")
except ImportError:
    USE_PROM = False


# ============================================================
# 🪟 Windows fix
# ============================================================
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ============================================================
# ⚙️ Config general
# ============================================================
MODEL_NAME = getattr(settings, "model_name", "sentence-transformers/all-MiniLM-L6-v2")
BATCH_LIMIT = getattr(settings, "batch_limit", 1000)
BATCH_SIZE = getattr(settings, "batch_size", 100)
ENCODE_BATCH_SIZE = getattr(settings, "encode_batch_size", 64)
MAX_WORDS = getattr(settings, "max_words", 250)
MAX_WORKERS = getattr(settings, "max_workers", 1)
ENCODE_TIMEOUT = getattr(settings, "encode_timeout", 120)
RETRY_HOURS = getattr(settings, "retry_hours", 24)

logger.info(f"🚀 Worker iniciado (PID={os.getpid()}, container={os.environ.get('HOSTNAME','local')})")


# ============================================================
# 🧠 Modelo singleton
# ============================================================
@lru_cache(maxsize=1)
def get_model(_factory: Callable[[], SentenceTransformer] = None):
    factory = _factory or (lambda: SentenceTransformer(MODEL_NAME))
    logger.info(f"🔹 Cargando modelo: {MODEL_NAME}")
    return factory()

EXPECTED_DIM = get_model().get_sentence_embedding_dimension()


# ============================================================
# 🧵 ThreadPool seguro
# ============================================================
encoder_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

def _safe_shutdown():
    try:
        encoder_pool.shutdown(wait=True)
        logger.info("✅ ThreadPool cerrado correctamente.")
    except RuntimeError:
        logger.warning("⚠️ ThreadPool ya estaba cerrado.")

atexit.register(_safe_shutdown)
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))


# ============================================================
# 🧩 Embedding async
# ============================================================
async def embed_text(texts: Union[str, List[str]]) -> List[List[float]]:
    loop = asyncio.get_event_loop()
    texts = [texts] if isinstance(texts, str) else texts

    def _encode():
        model = get_model()
        try:
            return model.encode(
                texts,
                batch_size=ENCODE_BATCH_SIZE,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
        except Exception as e:
            logger.error(f"💥 Error interno en encode(): {e}")
            return [None] * len(texts)

    try:
        return await asyncio.wait_for(
            loop.run_in_executor(encoder_pool, _encode),
            timeout=ENCODE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error("⏰ Timeout generando embeddings.")
        raise


# ============================================================
# 🧰 Preprocesamiento
# ============================================================
def preprocess(post: Post) -> str:
    return " ".join(((post.title or "") + " " + (post.body or "")).split())[:MAX_WORDS]


# ============================================================
# 🔁 Batch con reintento (incluye FIX CRÍTICO)
# ============================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def process_batch(batch: List[Post], texts: List[str]) -> None:

    async with async_session_maker() as session:
        try:
            timer = emb_dur.time() if USE_PROM else nullcontext()
            with timer:
                embs = await embed_text(texts)

            now = datetime.utcnow()

            for p, e, t in zip(batch, embs, texts):

                # ============================================================
                # ❗ FIX: RECARGAR POST DESDE LA SESIÓN ACTUAL
                # ============================================================
                db_post = await session.get(Post, p.pid)
                if db_post is None:
                    logger.error(f"❌ Post {p.pid} no existe en BD")
                    continue

                db_post.embedding_attempt_at = now

                if not t.strip():
                    logger.warning(f"⚠️ Post vacío: {p.pid}")
                    if USE_PROM: emb_fail.inc()
                    continue

                if e is None:
                    logger.warning(f"⚠️ Embedding nulo: {p.pid}")
                    if USE_PROM: emb_fail.inc()
                    continue

                e_np = np.asarray(e, dtype=np.float32).squeeze()

                if e_np.shape[0] != EXPECTED_DIM:
                    logger.warning(f"⚠️ Dim incorrecta {e_np.shape[0]} ≠ {EXPECTED_DIM} en {p.pid}")
                    if USE_PROM: emb_fail.inc()
                    continue

                # asignar embedding real al objeto cargado
                db_post.embedding = e_np.tolist()
                if USE_PROM: emb_ok.inc()

            await session.commit()

        except Exception as e:
            logger.exception(f"💥 Error batch: {e}")
            await session.rollback()
            raise


# ============================================================
# 🚀 Pipeline principal
# ============================================================
async def embed_all_posts(limit: int = BATCH_LIMIT) -> None:

    cutoff = datetime.utcnow() - timedelta(hours=RETRY_HOURS)

    # leer posts que necesitan embedding
    async with async_session_maker() as session:
        result = await session.execute(
            select(Post)
            .where(
                Post.embedding.is_(None),
                (Post.embedding_attempt_at.is_(None)) | (Post.embedding_attempt_at < cutoff),
            )
            .order_by(Post.created_at)
            .limit(limit)
        )
        posts = result.scalars().all()

    if not posts:
        logger.info("✅ No hay posts pendientes.")
        return

    total = len(posts)
    logger.info(f"📦 {total} posts pendientes.")

    for i in range(0, total, BATCH_SIZE):

        batch = posts[i : i + BATCH_SIZE]
        texts = [preprocess(p) for p in batch]

        try:
            await process_batch(batch, texts)
            logger.info(f"✅ Batch {i//BATCH_SIZE + 1} procesado ({len(batch)} posts)")

        except Exception as e:
            logger.exception(f"🔥 Batch falló: {e}")

            # marcar intentos en caso de fallo
            async with async_session_maker() as session:
                now = datetime.utcnow()
                await session.execute(
                    update(Post)
                    .where(Post.pid.in_([p.pid for p in batch]))
                    .values(embedding_attempt_at=now)
                )
                await session.commit()

    logger.info("🎯 Embeddings completados.")


# ============================================================
# 🧹 Entry point
# ============================================================
async def main():
    await embed_all_posts()

if __name__ == "__main__":
    asyncio.run(main())

