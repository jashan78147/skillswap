"""
database.py -- the connection to your database.

Works in two modes, chosen automatically:

  * LOCAL  (your laptop)  -> SQLite, a single file next to this project.
    Nothing to install, nothing to configure.

  * HOSTED (Render/Neon)  -> PostgreSQL, read from the DATABASE_URL
    environment variable that the host provides.

Nothing in the rest of the app has to know which one is in use.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Where the local SQLite file lives: backend/skillswap.db
BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "skillswap.db"

# An "environment variable" is a setting that lives outside your code --
# set by the hosting service, not written in a file. That is how secrets
# like database passwords stay out of GitHub.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def _normalise(url: str) -> str:
    """
    Hosting providers hand out URLs starting with `postgres://`, which is an
    old spelling SQLAlchemy no longer accepts. It also needs to be told which
    driver to use. This rewrites the URL into the form it expects:

        postgres://user:pw@host/db
        -> postgresql+psycopg://user:pw@host/db
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


if DATABASE_URL:
    # ---------------------------------------------------------- hosted --
    DATABASE_URL = _normalise(DATABASE_URL)

    engine = create_engine(
        DATABASE_URL,
        # Free hosting tiers drop idle connections. pool_pre_ping quietly
        # tests a connection before using it and reopens it if it is dead,
        # instead of failing the request with a confusing error.
        pool_pre_ping=True,
        pool_recycle=300,
    )
    IS_SQLITE = False
else:
    # ----------------------------------------------------------- local --
    DATABASE_URL = f"sqlite:///{DB_FILE}"

    engine = create_engine(
        DATABASE_URL,
        # Required for SQLite + FastAPI: requests may arrive on different
        # threads, and SQLite is cautious about that by default.
        connect_args={"check_same_thread": False},
    )
    IS_SQLITE = True


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Every table class in models.py inherits from this."""
    pass


def get_db():
    """
    Hands a fresh database session to whichever endpoint needs one, then
    guarantees it gets closed afterwards -- even if an error happened.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
