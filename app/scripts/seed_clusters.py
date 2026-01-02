import asyncio
import numpy as np
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
from sqlmodel import SQLModel
from app.db.database import async_session_maker
from app.db.models_sqlmodel import InsightsCluster

# ============================================================
# 🧠 Configuración general
# ============================================================

N_DIM = 384  # Dimensión del embedding (Sentence-BERT compatible)


def random_embedding(dim=384):
    """Genera un vector aleatorio único y normalizado (norma L2 = 1)."""
    rng = np.random.default_rng(int(uuid.uuid4().int % 1e9))  # semilla única
    vec = rng.normal(0, 1, dim).astype(np.float32)
    vec /= np.linalg.norm(vec)  # normalización L2
    return vec.tolist()


# ============================================================
# 🧩 Generador de clusters falsos
# ============================================================

def fake_cluster(i: int):
    """Crea un diccionario con datos simulados de un cluster."""
    return {
        "id": f"cluster_{i}",
        "vertical": np.random.choice(["fitness", "nootropics", "supplements"]),
        "label": f"Cluster {i}",
        "n_posts": np.random.randint(50, 500),
        "centroid": random_embedding(),
        "source_forum": np.random.choice(["Reddit", "Discord", "Twitter"]),
        "last_post_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
    }


# ============================================================
# 🚀 Seeder principal
# ============================================================

async def seed_clusters(n: int = 100):
    """
    Inserta clusters falsos en la base de datos de forma idempotente.
    Usa ON CONFLICT DO NOTHING para evitar duplicados.
    """
    async with async_session_maker() as session:
        # Recupera la tabla mapeada en SQLModel.metadata
        table = SQLModel.metadata.tables.get("insights_clusters")

        if table is None:
            print("❌ Tabla 'insights_clusters' no encontrada en metadata.")
            return

        # Construcción del INSERT idempotente
        stmt = (
            insert(table)
            .values([fake_cluster(i) for i in range(n)])
            .on_conflict_do_nothing(index_elements=["id"])
        )

        # Ejecución del insert
        await session.execute(stmt)
        await session.commit()
        print(f"✅ Insertados {n} clusters (sin duplicar existentes).")

        # Validación y conteo final
        result = await session.execute(text("SELECT COUNT(*) FROM insights_clusters"))
        count = result.scalar()
        print(f"📊 Total de registros en insights_clusters: {count}")


# ============================================================
# 🏁 Entry point
# ============================================================

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    asyncio.run(seed_clusters(n))
