# app/ml/predict_filter.py
from app.core.settings import settings
from app.core.logger import logger

def load_model(vertical: str):
    logger.info(f"Loading ML model for vertical {vertical}")
    return {"vertical": vertical, "model": "dummy_model"}

def predict(model, text: str) -> bool:
    logger.debug(f"Predicting text: {text}")
    return "problem" in text.lower()

# -----------------------------
# Función que necesita la pipeline
# -----------------------------
def classify_problem(text: str):
    model = load_model(settings.vertical)
    is_problem = predict(model, text)
    # Retornamos categoría y confianza dummy
    category = "problem" if is_problem else "other"
    confidence = 0.99 if is_problem else 0.5
    return category, confidence
