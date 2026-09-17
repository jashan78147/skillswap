"""
main.py -- the entry point. Running the server runs this file.

Responsibilities:
  1. Create the FastAPI application
  2. Decide which web addresses are allowed to call it (CORS)
  3. Make sure the database tables exist
  4. Seed demo data on a brand new database
  5. Plug in the routers that define the actual URLs
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app import models
from app.routers import admin, auth, matches, ratings, skills, swaps, users
from app.security import hash_password

# ---------------------------------------------------------------------
# Build any missing tables on startup, so a fresh deployment works with
# no manual setup step.
# ---------------------------------------------------------------------
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------
# Seed demo data, but ONLY on a completely empty database.
#
# Free hosting tiers give no shell access, so there is no way to run
# seed.py by hand after deploying. This does it automatically, and the
# "only if empty" guard means it can never overwrite real data.
#
# A "lifespan" function runs once when the server starts. Everything
# before `yield` happens at startup; anything after runs at shutdown.
# ---------------------------------------------------------------------
def _seed_if_empty() -> None:
    """Populate demo data, but only when there are no users at all."""
    if os.environ.get("SEED_ON_START", "").lower() not in ("1", "true", "yes"):
        return

    db = SessionLocal()
    try:
        has_users = db.scalar(select(models.User).limit(1)) is not None
    finally:
        db.close()

    if has_users:
        return

    try:
        import seed
        seed.main()
        print("[startup] empty database detected -- demo data seeded")
    except Exception as exc:  # never let seeding stop the server booting
        print(f"[startup] seeding skipped: {exc}")


def _ensure_admin() -> None:
    """
    Make sure at least one administrator exists.

    The normal rule -- "the first account on an empty database becomes the
    admin" -- cannot fire on a deployed site, because seeding fills the
    database before anyone signs up. Without this, the admin panel would be
    permanently unreachable.

    Credentials come from environment variables, so they are never written
    into the repository. Does nothing once an admin exists, so it is safe on
    every restart.
    """
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")

    if not email:
        return

    db = SessionLocal()
    try:
        if db.scalar(select(models.User).where(models.User.is_admin.is_(True))):
            return  # an admin already exists, nothing to do

        existing = db.scalar(select(models.User).where(models.User.email == email))

        if existing is not None:
            existing.is_admin = True
            if password:
                existing.password_hash = hash_password(password)
            db.commit()
            print(f"[startup] promoted {email} to administrator")
        elif password:
            db.add(models.User(
                name=os.environ.get("ADMIN_NAME", "Administrator"),
                email=email,
                password_hash=hash_password(password),
                is_admin=True,
            ))
            db.commit()
            print(f"[startup] created administrator account {email}")
        else:
            print("[startup] ADMIN_EMAIL set but ADMIN_PASSWORD missing -- no admin created")
    except Exception as exc:
        print(f"[startup] admin setup skipped: {exc}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _seed_if_empty()
    _ensure_admin()
    yield  # the server runs for as long as this is paused here


app = FastAPI(
    title="SkillSwap API",
    description="Peer-to-peer skill exchange platform.",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------
# CORS -- which web addresses may call this API.
#
# Browsers block a page on one address from calling a different address,
# to stop a malicious site quietly using your logged-in session elsewhere.
# Our frontend and backend are on different addresses, so the backend has
# to say explicitly which frontends it expects.
# ---------------------------------------------------------------------

# Local development. Vite normally uses 5173 but silently moves to 5174 or
# 5175 if that port is busy, so a few spares are listed.
LOCAL_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
    "http://localhost:5175", "http://127.0.0.1:5175",
    "http://localhost:3000", "http://127.0.0.1:3000",
]

# The deployed frontend address, supplied by the host as an environment
# variable. Comma-separated so more than one can be listed.
EXTRA_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS + EXTRA_ORIGINS,
    # Vercel gives every deployment its own preview address, such as
    # skillswap-abc123.vercel.app. Listing them one by one is impossible,
    # so this pattern accepts any of them.
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Plug in the URL groups.
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(skills.router)
app.include_router(swaps.router)
app.include_router(ratings.router)
app.include_router(matches.router)
app.include_router(admin.router)
app.include_router(admin.public_router)


@app.get("/", tags=["system"])
def root():
    """
    A friendly landing response for the bare URL.

    Without this, visiting the root address returns {"detail":"Not Found"},
    which looks broken even though the API is running perfectly. This points
    whoever opened it at something useful instead.
    """
    return {
        "service": "SkillSwap API",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
        "message": "This is the backend API. The web app is deployed separately.",
    }


@app.get("/api/health", tags=["system"])
def health_check():
    """
    A trivial endpoint that just says "I'm alive".

    Also useful for waking a free-tier server that has gone to sleep:
    open this a minute before a demo and the first real page load is fast.
    """
    from app.database import IS_SQLITE
    return {
        "status": "ok",
        "service": "SkillSwap API",
        "database": "sqlite" if IS_SQLITE else "postgresql",
    }
