# app/db/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlmodel import SQLModel
from app.core.settings import settings

# ------------------------------------------------------------------
# 1️⃣ URLs NORMALIZADAS (CLAVE)
# ------------------------------------------------------------------
raw_url = str(settings.database_url)

# 🔹 Sync engine → SIEMPRE psycopg3
sync_url = (
    raw_url
    .replace("postgresql+asyncpg://", "postgresql+psycopg://")
    .replace("postgresql://", "postgresql+psycopg://")
)

# 🔹 Async engine → SIEMPRE asyncpg
async_url = (
    raw_url
    if raw_url.startswith("postgresql+asyncpg")
    else raw_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
)

# ------------------------------------------------------------------
# 2️⃣ Echo solo en dev
# ------------------------------------------------------------------
echo = getattr(settings, "env", "dev") == "dev"

# ------------------------------------------------------------------
# 3️⃣ Engines
# ------------------------------------------------------------------
engine = create_engine(sync_url, echo=echo)
async_engine = create_async_engine(async_url, echo=echo)

# ------------------------------------------------------------------
# 4️⃣ Sesiones
# ------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

async_session_maker = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ------------------------------------------------------------------
# 5️⃣ Dependency async
# ------------------------------------------------------------------
async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
