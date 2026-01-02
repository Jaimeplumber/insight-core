# app/ml/embeddings.py

import numpy as np
from functools import lru_cache
from fastapi import HTTPException

try:
    from prometheus_client import Counter
    USE_PROM = True
    query_counter = Counter("semantic_queries_total", "Consultas semánticas recibidas")
except ImportError:
    USE_PROM = False
    query_counter = None

from sentence_transformers import SentenceTransformer


# ============================================================
# 🧠 Modelo singleton
# ============================================================
@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return model


EXPECTED_DIM = get_model().get_sentence_embedding_dimension()   # ≈ 384


# ============================================================
# 🧩 Embedder principal (producción)
# ============================================================
def embed_query(text: str) -> np.ndarray:
    """Genera un embedding normalizado para búsquedas semánticas."""
    if not text or not text.strip():
        raise HTTPException(400, "El texto no puede estar vacío.")

    if USE_PROM:
        query_counter.inc()

    model = get_model()

    try:
        emb = model.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False
        )
    except Exception as e:
        raise HTTPException(500, f"Error generando embedding: {str(e)}")

    # Convertir a float32 y aplastar
    emb = np.asarray(emb, dtype=np.float32).squeeze()

    # ============================================================
    # 🚨 Validación fuerte (exactamente 384 dimensiones)
    # ============================================================
    if emb.ndim != 1 or emb.shape[0] != EXPECTED_DIM:
        raise HTTPException(
            500,
            f"Dimensión inesperada del embedding: {emb.shape}, se esperaba {EXPECTED_DIM}"
        )

    return emb


# ============================================================
# ⚡ Cache LRU para queries repetidas (micro-optimización)
# ============================================================
@lru_cache(maxsize=1024)
def cached_embed_query(text: str) -> np.ndarray:
    """Versión cacheada para queries repetidas."""
    text = text.strip().lower()
    return embed_query(text)
