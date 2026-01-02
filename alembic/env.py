# alembic/env.py

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel
from alembic import context
import os
import sys

# ------------------------------------------------------------
# 🔧 Aseguramos que Alembic encuentre "app/"
# ------------------------------------------------------------
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.settings import settings
from app.db.database import engine
from app.db.models_sqlmodel import Post  # importa tus modelos para autogenerate

# ------------------------------------------------------------
# ⚙️ Configuración base de Alembic
# ------------------------------------------------------------
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ------------------------------------------------------------
# 🧩 Metadata principal (SQLModel)
# ------------------------------------------------------------
target_metadata = SQLModel.metadata

# ------------------------------------------------------------
# 🔄 Funciones de migración
# ------------------------------------------------------------
def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo offline."""
    context.configure(
        url=settings.database_url.replace("+asyncpg", ""),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo online (normal)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=settings.database_url.replace("+asyncpg", ""),  # ✅ Usa sync URL
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# ------------------------------------------------------------
# 🚀 Ejecución
# ------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
