import pytest
from app.db.models import Post
from datetime import datetime

@pytest.fixture
def create_posts(db_session):
    """
    Fixture para crear posts de prueba en la DB.
    Se puede llamar con distintos datos de posts.
    """
    def _create_posts(posts_data):
        posts = [Post(**data) for data in posts_data]
        db_session.add_all(posts)
        db_session.commit()
        return posts
    return _create_posts