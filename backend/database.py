import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from models import Base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "smartshift.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    """Einfache Auto-Migration: fügt neue Spalten zu bestehenden Tabellen hinzu."""
    inspector = inspect(engine)
    if "shift_requirements" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("shift_requirements")}
    new_cols = {
        "is_daily": "BOOLEAN DEFAULT 0",
        "valid_from": "DATE",
        "valid_until": "DATE",
    }
    with engine.begin() as conn:
        for col, ddl in new_cols.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE shift_requirements ADD COLUMN {col} {ddl}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
