# app/enrichment/search_sqlmodel.py
from sqlmodel import select
from sqlalchemy import text
from app.db.database import async_session_maker
from app.ml.embedder import embed_text
import asyncio


async def search_similar_posts(query: str, limit: int = 5):
    """
    Busca posts similares a un texto usando similitud coseno (pgvector).
    """
    embedding = embed_text(query)

    sql = text("""
        SELECT pid, title, body, category, confidence,
               1 - (embedding <=> :embedding) AS similarity
        FROM posts_sqlmodel
        WHERE enriched_at IS NOT NULL
        ORDER BY embedding <=> :embedding
        LIMIT :limit
    """)

    async with async_session_maker() as session:
        result = await session.execute(sql, {"embedding": embedding, "limit": limit})
        rows = result.fetchall()

        print(f"🔍 Resultados similares a: '{query}'")
        for pid, title, body, category, confidence, similarity in rows:
            print(f"→ ({similarity:.3f}) {title[:60]} [{category}]")
        return rows


if __name__ == "__main__":
    asyncio.run(search_similar_posts("protein powder vegan", limit=5))
