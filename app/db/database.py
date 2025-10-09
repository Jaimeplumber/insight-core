# app/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base, sessionmaker

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.settings import settings

# ---------------------------
# Síncrono (ya existente)
# ---------------------------
SQLALCHEMY_DATABASE_URL = settings.database_url
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------
# Asíncrono (para pipeline async)
# ---------------------------
# SQLite async URL: "sqlite+aiosqlite:///./problems.db"
ASYNC_SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
async_engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL, echo=True
)
async_session_maker = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()
