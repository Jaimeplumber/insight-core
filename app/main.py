from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func

from app.api.routes import insights
from app.api.deps import AsyncDbDep
from app.core.settings import settings
from app.core.logger import logger
from app.db.database import async_engine
from app.db.models_sqlmodel import Post


# ------------------------------------------------------------------
# Lifespan: crear tablas en dev
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("InsightCore starting...")

    if settings.env == "dev":
        try:
            async with async_engine.begin() as conn:
                await conn.run_sync(Post.metadata.create_all)
            logger.info("Dev tables created")
        except Exception:
            logger.error("Error creating dev tables", exc_info=True)
            raise

    yield

    try:
        await async_engine.dispose()
        logger.info("DB engine disposed")
    except Exception:
        logger.error("Error disposing engine", exc_info=True)


# ------------------------------------------------------------------
# FastAPI App (sin atributos inexistentes en settings)
# ------------------------------------------------------------------
app = FastAPI(
    title="Insight Core API",
    version="1.0.0",                    # ← Fijo y seguro
    description="Insights API backend",  # ← Seguro también
    lifespan=lifespan,
    docs_url="/docs" if settings.env != "prod" else None,
    redoc_url="/redoc" if settings.env != "prod" else None,
)


# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Global exception handler
# ------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "data": None,
            "message": "Internal server error",
        },
    )


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
PROBE_TIMEOUT = 5


@app.get("/health", tags=["system"])
async def health(db: AsyncDbDep):
    try:
        async with asyncio.timeout(PROBE_TIMEOUT):
            total = await db.scalar(
                select(func.count(Post.pid)).where(Post.vertical == settings.vertical)
            )

        return {
            "status": "ok",
            "db": "up",
            "vertical": settings.vertical,
            "total_posts": total,
        }

    except Exception as e:
        logger.error("Health check failed", exc_info=True)
        detail = str(e) if settings.env != "prod" else "unreachable"

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "down",
                "db": "unreachable",
                "detail": detail,
            },
        )


# ------------------------------------------------------------------
# Readiness probe
# ------------------------------------------------------------------
@app.get("/ready", tags=["system"])
async def ready(db: AsyncDbDep):
    try:
        async with asyncio.timeout(PROBE_TIMEOUT):
            await db.execute(select(1))

        return {"status": "ready"}

    except Exception as e:
        logger.error("Readiness probe failed", exc_info=True)
        detail = str(e) if settings.env != "prod" else "not_ready"

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "detail": detail},
        )


# ------------------------------------------------------------------
# Mount Insights routes
# ------------------------------------------------------------------
app.include_router(
    insights.router,
    prefix="/api/v1/insights",
    tags=["Insights"],
)

