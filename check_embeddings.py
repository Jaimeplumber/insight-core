import asyncio
from app.db.database import async_session_maker
from app.db.models_sqlmodel import Post
from sqlalchemy.future import select


async def check_posts():
    async with async_session_maker() as session:
        result = await session.execute(select(Post))
        posts = result.scalars().all()   # <-- 🔥 AQUÍ LA CORRECCIÓN

        for p in posts:
            has_emb = p.embedding is not None and len(p.embedding) == 384
            print(
                f"{p.pid} | embedding: {has_emb} | attempt_at: {p.embedding_attempt_at}"
            )

asyncio.run(check_posts())
