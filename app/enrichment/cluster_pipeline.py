# app/enrichment/cluster_pipeline.py
import asyncio
import numpy as np
from datetime import datetime, timezone
from sqlmodel import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import async_session_maker
from app.db.models_sqlmodel import Post
from app.db.models_clusters import Cluster
from app.ml.clustering import cluster_embeddings
from app.ml.embedder import embed_text
from app.core.settings import settings
from app.core.logger import logger


async def cluster_posts():
    """
    Agrupa posts enriquecidos (con embeddings) en clusters semánticos.
    - Usa HDBSCAN (basado en densidad)
    - Calcula centroides
    - Guarda resumen y metadatos (n_posts, last_post_at)
    """
    async with async_session_maker() as session:
        try:
            # 1️⃣ Obtener todos los posts con embeddings disponibles
            result = await session.execute(
                select(Post)
                .where(
                    Post.vertical == settings.vertical,
                    Post.embedding.is_not(None),
                    Post.enriched_at.is_not(None)
                )
            )
            posts = result.scalars().all()

            if not posts:
                logger.warning("⚠️ No hay embeddings disponibles para clusterizar.")
                return {"vertical": settings.vertical, "clusters": 0, "posts": 0}

            logger.info("🧩 Obtenidos %s posts enriquecidos para %s", len(posts), settings.vertical)

            # 2️⃣ Ejecutar clustering
            embeddings = [np.array(p.embedding, dtype=np.float32) for p in posts]
            labels, n_clusters = cluster_embeddings(embeddings)

            if n_clusters == 0:
                logger.info("⚠️ No se formaron clusters válidos.")
                return {"vertical": settings.vertical, "clusters": 0, "posts": len(posts)}

            logger.info("🧠 Detectados %s clusters válidos", n_clusters)

            # 3️⃣ Crear objetos Cluster para DB
            clusters_data = []
            now = datetime.now(timezone.utc)

            for cluster_id in set(labels):
                if cluster_id == -1:
                    continue  # -1 = ruido

                cluster_posts = [p for p, label in zip(posts, labels) if label == cluster_id]
                centroid = np.mean([p.embedding for p in cluster_posts], axis=0).tolist()
                joined_titles = " | ".join([p.title for p in cluster_posts])

                # 🔹 Resumen semántico (por ahora placeholder)
                summary_text = f"Theme of {len(cluster_posts)} posts: {joined_titles[:120]}..."
                label = f"Cluster {cluster_id}"

                clusters_data.append(
                    Cluster(
                        vertical=settings.vertical,
                        label=label,
                        summary=summary_text,
                        n_posts=len(cluster_posts),
                        source_forum="reddit",  # o lo que corresponda
                        last_post_at=max([p.created_at for p in cluster_posts]),
                        centroid=centroid,
                        created_at=now,
                    )
                )

            # 4️⃣ Guardar clusters en la DB
            session.add_all(clusters_data)
            await session.commit()

            logger.info("✅ Guardados %s clusters en la DB para '%s'", len(clusters_data), settings.vertical)

            return {
                "vertical": settings.vertical,
                "clusters": len(clusters_data),
                "posts": len(posts),
            }

        except SQLAlchemyError:
            logger.error("❌ Error SQLAlchemy en clusterización", exc_info=True)
            await session.rollback()
        except Exception:
            logger.error("❌ Error inesperado en clusterización", exc_info=True)
            await session.rollback()


if __name__ == "__main__":
    result = asyncio.run(cluster_posts())
    print("\nResultado final:", result)
