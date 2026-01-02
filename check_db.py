# check_db.py
import sys, os
sys.path.insert(0, os.getcwd())

from app.core.settings import settings          # <-- 1. ruta correcta
from app.db.models_sqlmodel import Post
from sqlmodel import create_engine, inspect

engine = create_engine(settings.database_url.get_secret_value())  # <-- 2. extrae el secreto
insp = inspect(engine)

print("Tablas:", insp.get_table_names())
if "posts_sqlmodel" in insp.get_table_names():
    print("\nColumnas en posts_sqlmodel:")
    for col in insp.get_columns("posts_sqlmodel"):
        print(f" - {col['name']} ({col['type']})")
else:
    print("❌ posts_sqlmodel no existe")