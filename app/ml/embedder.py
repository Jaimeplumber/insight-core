# app/ml/embedder.py
import logging
import torch
from functools import lru_cache
from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# ⚙️ Configuración del dispositivo (CPU / GPU automática)
# ----------------------------------------------------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"


# ----------------------------------------------------------------------
# 🧠 Carga perezosa del modelo (solo 1 vez en todo el proceso)
# ----------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """
    Carga el modelo de embeddings con caché en memoria.
    Usa un modelo de 384 dimensiones compatible con pgvector.
    """
    model_name = "all-MiniLM-L6-v2"
    logger.info(f"Loading embedding model '{model_name}' on {device}")
    model = SentenceTransformer(model_name, device=device)
    return model


# ----------------------------------------------------------------------
# 🔢 Genera embedding con fallback seguro
# ----------------------------------------------------------------------
def embed_text(text: str) -> List[float]:
    """
    Genera embedding de texto.
    - Normaliza embeddings (unit vector)
    - Devuelve lista de 384 floats
    - Si hay error, retorna vector nulo (fail-safe)
    """
    try:
        if not text.strip():
            return [0.0] * 384

        model = get_model()
        emb = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)

        # Asegurar dimensión fija (por seguridad)
        if emb.shape[0] != 384:
            logger.warning(f"Unexpected embedding size: {emb.shape[0]}")
            emb = np.resize(emb, (384,))

        return emb.tolist()

    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return [0.0] * 384


# ----------------------------------------------------------------------
# 🧪 Test rápido
# ----------------------------------------------------------------------
if __name__ == "__main__":
    vec = embed_text("Hola, este es un test del modelo de embeddings.")
    print(f"✅ Dimensión: {len(vec)} valores")
    print(f"Primeros 5 valores: {vec[:5]}")
