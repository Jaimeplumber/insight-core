# app/api/deps.py
from typing import Generator, AsyncGenerator, Annotated, TypeAlias
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import SessionLocal, async_session_maker
from app.core.logger import logger

# ---------- SYNC ----------
def get_db() -> Generator[Session, None, None]:
    """Sync DB dependency."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("DB session error", exc_info=True)
        raise
    finally:
        db.close()

DbDep: TypeAlias = Annotated[Session, Depends(get_db)]

# ---------- ASYNC ----------
async def get_db_async() -> AsyncGenerator[AsyncSession, None]:
    """Async DB dependency."""
    async with async_session_maker() as db:
        try:
            yield db
        except Exception as e:
            logger.error("Async DB session error", exc_info=True)
            raise

AsyncDbDep: TypeAlias = Annotated[AsyncSession, Depends(get_db_async)]

# ---------- TEST HELPERS ----------
def override_get_db() -> Generator[Session, None, None]:
    """Override for sync tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def override_get_db_async() -> AsyncGenerator[AsyncSession, None]:
    """Override for async tests."""
    async with async_session_maker() as db:
        yield db
