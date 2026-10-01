"""DB engine + session. Prod: PostgreSQL+PostGIS; demo: SQLite (same schema)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """Tiny idempotent migration for SQLite dev DBs: create_all does not add
    columns to tables that already exist, so patch in new columns by hand."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    from sqlalchemy import text
    wanted = {
        "evidence": [
            ("gps_lat", "NUMERIC"),
            ("gps_lon", "NUMERIC"),
            ("mime", "VARCHAR(20)"),
        ],
        "incidents": [
            ("impact_part", "VARCHAR(120)"),
            ("driver_comment", "TEXT"),
            ("injured_count", "INTEGER DEFAULT 0"),
        ],
    }
    with engine.begin() as conn:
        for table, cols in wanted.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for name, coltype in cols:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {coltype}"))

