from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///calls.db")
engine = create_engine(DATABASE_URL)


def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS calls (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id     TEXT UNIQUE,
                phone       TEXT,
                language    TEXT,
                intent      TEXT,
                query       TEXT,
                top_score   REAL,
                escalated   INTEGER DEFAULT 0,
                duration_s  INTEGER,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()


def log_call(data: dict):
    """
    data keys: call_id, phone, language, intent, query, top_score, escalated, duration_s
    """
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT OR IGNORE INTO calls
              (call_id, phone, language, intent, query, top_score, escalated, duration_s)
            VALUES
              (:call_id, :phone, :language, :intent, :query, :top_score, :escalated, :duration_s)
        """), data)
        conn.commit()
