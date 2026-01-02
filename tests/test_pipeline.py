# tests/test_pipeline.py
import pytest
from datetime import datetime
from app.db.database import Base, engine, SessionLocal
from app.db.models import Post
from app.enrichment.pipeline import run_enrichment_pipeline


# ------------------------------------------------------------------
# FIXTURE: Base de datos limpia antes/despúes del módulo
# ------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ------------------------------------------------------------------
# FIXTURE: Factory para crear posts + cleanup automático
# ------------------------------------------------------------------
@pytest.fixture
def create_posts():
    def _create_posts(posts_data):
        with SessionLocal() as session:
            posts = [Post(**data) for data in posts_data]
            session.add_all(posts)
            session.commit()
            for p in posts:
                session.refresh(p)
            return posts
    yield _create_posts
    # Cleanup: borra TODOS los posts (simple y efectivo)
    with SessionLocal() as session:
        session.query(Post).delete(synchronize_session=False)
        session.commit()


# ------------------------------------------------------------------
# TEST BÁSICO
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pipeline_basic(create_posts):
    posts_data = [
        {"title": "Test problem 1", "body": "Water leakage", "vertical": "insights"},
        {"title": "No problem", "body": "General info", "vertical": "insights"},
        {"title": "Low pressure", "body": "Customer reports issue", "vertical": "insights"},
    ]
    posts = create_posts(posts_data)

    result = await run_enrichment_pipeline(limit=10)
    assert result["processed"] == len(posts)

    with SessionLocal() as session:
        enriched = session.query(Post).filter(Post.enriched_at.is_not(None)).all()
        assert len(enriched) == len(posts)
        for post in enriched:
            print(f"{post.title} enriched at {post.enriched_at}")


# ------------------------------------------------------------------
# TEST PARAMETRIZADO: distintos verticales
# ------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("vertical,expected_count", [("insights", 3), ("news", 2)])
async def test_pipeline_multiple_verticals(vertical, expected_count, create_posts):
    posts_data = [
        {"title": f"Post {i}", "body": f"Body {i}", "vertical": vertical}
        for i in range(expected_count)
    ]
    create_posts(posts_data)

    result = await run_enrichment_pipeline(limit=10)
    assert result["processed"] == expected_count
    assert result["vertical"] == vertical  # ✅ más clara y consistente


# ------------------------------------------------------------------
# TEST: sin posts → 0 procesados
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pipeline_no_rows():
    result = await run_enrichment_pipeline(limit=10)
    assert result["processed"] == 0
@pytest.mark.asyncio
async def test_pipeline_ml_integration(create_posts):
    """Verifica que los campos del modelo ML se actualicen correctamente."""
    posts_data = [
        {"title": "Water leak under sink", "body": "Customer reports a leak near kitchen sink", "vertical": "insights"},
    ]
    posts = create_posts(posts_data)

    result = await run_enrichment_pipeline(limit=1)
    assert result["processed"] == 1

    with SessionLocal() as session:
        post = session.query(Post).filter_by(pid=posts[0].pid).first()
        assert post is not None, "El post debería existir"
        assert post.enriched_at is not None, "El campo enriched_at no fue actualizado"
        assert post.category is not None, "El campo category debería estar enriquecido"
        assert post.confidence is not None and post.confidence > 0, "Confidence debería tener un valor positivo"

        # Opcional: si tu pipeline genera summary o tags
        if hasattr(post, "summary"):
            print(f"🧠 Summary: {post.summary}")
        if hasattr(post, "tags"):
            print(f"🏷️ Tags: {post.tags}")

    print(f"✅ Post enriquecido → category={post.category}, confidence={post.confidence}")