import asyncio
import os
import sys
import time
from datetime import datetime
from sqlalchemy import text
from app.db.database import async_session_maker
from app.core.logger import logger
from app.core.settings import settings

# ============================================================
# 🪟 Fix para Windows
# ============================================================
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ============================================================
# ⚙️ Configuración
# ============================================================
REFRESH_INTERVAL = int(os.getenv("MONITOR_INTERVAL", 60))  # segundos
TOTAL_LIMIT = int(os.getenv("TOTAL_POSTS_EXPECTED", 0))     # opcional, si lo sabes de antemano
AVG_WINDOW = 5  # número de muestras para suavizar el promedio

# ============================================================
# 🚀 Función principal
# ============================================================
async def monitor_loop():
    logger.info("📊 Monitor de embeddings iniciado.")
    logger.info(f"⏱️ Actualizando cada {REFRESH_INTERVAL} segundos...")

    samples = []
    start_time = time.time()
    last_count = None

    while True:
        try:
            async with async_session_maker() as session:
                # Posts pendientes
                res = await session.execute(
                    text("SELECT COUNT(*) FROM posts_sqlmodel WHERE embedding IS NULL;")
                )
                pending = res.scalar()

                # Posts totales (si no se proporcionó)
                if TOTAL_LIMIT == 0:
                    total_res = await session.execute(
                        text("SELECT COUNT(*) FROM posts_sqlmodel;")
                    )
                    total = total_res.scalar()
                else:
                    total = TOTAL_LIMIT

                processed = total - pending
                progress = processed / total * 100 if total else 0

                # Cálculo de velocidad
                if last_count is not None and pending < last_count:
                    delta = last_count - pending
                    samples.append(delta / (REFRESH_INTERVAL / 60))  # posts/min
                    if len(samples) > AVG_WINDOW:
                        samples.pop(0)
                last_count = pending

                avg_speed = sum(samples) / len(samples) if samples else 0
                elapsed = (time.time() - start_time) / 60

                logger.info(
                    f"📦 Pendientes: {pending:,} | 🧠 Procesados: {processed:,}/{total:,} ({progress:.1f}%) | ⚡ {avg_speed:.1f} posts/min | ⏳ {elapsed:.1f} min"
                )

            await asyncio.sleep(REFRESH_INTERVAL)

        except KeyboardInterrupt:
            logger.warning("🛑 Monitor detenido manualmente.")
            break
        except Exception as e:
            logger.error(f"💥 Error en monitor: {e}")
            await asyncio.sleep(REFRESH_INTERVAL)

# ============================================================
# 🧹 Entry point
# ============================================================
async def main():
    await monitor_loop()

if __name__ == "__main__":
    asyncio.run(main())
