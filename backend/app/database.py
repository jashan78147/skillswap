"""
database.py -- the connection to your database file.

Plain English:
  * SQLite stores your whole database in ONE file: skillswap.db
  * The "engine" is the thing that knows how to open that file.
  * A "session" is one short conversation with the database
    (open it, ask questions, save changes, close it).
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Where the database file lives: backend/skillswap.db
# Path(__file__) is THIS file. .parent goes up one folder (app/),
# .parent again goes up to backend/. So the .db sits next to requirements.txt.
BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "skillswap.db"

# The "connection string" tells SQLAlchemy: use sqlite, at this exact path.
DATABASE_URL = f"sqlite:///{DB_FILE}"

# check_same_thread=False is required for SQLite + FastAPI.
# Reason: FastAPI may handle requests on different threads, and SQLite
# is cautious about that by default. This tells it we know what we're doing.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# A factory that produces new sessions on demand.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Every table class in models.py inherits from this."""
    pass


def get_db():
    """
    Hands a fresh database session to whichever endpoint needs one,
    then guarantees it gets closed afterwards -- even if an error happened.

    The 'yield' keyword means: give this out, wait until the caller is
    finished, then run the cleanup line below.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
