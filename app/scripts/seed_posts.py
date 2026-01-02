# app/scripts/seed_posts.py
import asyncio
import uuid
from sqlmodel import select
from sqlalchemy.exc import SQLAlchemyError
from app.db.database import async_session_maker
from app.db.models_sqlmodel import Post
from app.core.settings import settings
from app.core.logger import logger


async def seed_posts(n: int = 3):
    """Inserta n posts de prueba de forma idempotente."""
    async with async_session_maker() as session:
        try:
            # Verificar si ya existen posts para esta vertical
            result = await session.execute(
                select(Post).where(Post.vertical == settings.vertical)
            )
            if result.scalars().first():
                logger.info("⚠️ Ya existen posts para vertical '%s'", settings.vertical)
                return

            # Crear posts dummy
            posts = [
                Post(
                    pid=str(uuid.uuid4()),
                    title="Best protein powder for muscle growth?",
                    body="I'm looking for a vegan protein that tastes good and mixes well.",
                    vertical=settings.vertical,
                ),
                Post(
                    pid=str(uuid.uuid4()),
                    title="Pre-workout without caffeine?",
                    body="Any suggestions for pre-workouts that don’t cause jitters?",
                    vertical=settings.vertical,
                ),
                Post(
                    pid=str(uuid.uuid4()),
                    title="Electrolytes for runners",
                    body="Do I really need to supplement electrolytes for short runs?",
                    vertical=settings.vertical,
                ),
            ]

            session.add_all(posts)
            await session.commit()

            logger.info("✅ Insertados %s posts para vertical '%s'", len(posts), settings.vertical)

        except SQLAlchemyError as e:
            logger.error("❌ Error al insertar posts: %s", e, exc_info=True)
            await session.rollback()
        except Exception as e:
            logger.error("❌ Error inesperado: %s", e, exc_info=True)
            await session.rollback()


if __name__ == "__main__":
    asyncio.run(seed_posts())
