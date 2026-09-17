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
@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.environ.get("SEED_ON_START", "").lower() in ("1", "true", "yes"):
        db = SessionLocal()
        try:
            has_users = db.scalar(select(models.User).limit(1)) is not None
        finally:
            db.close()

        if not has_users:
            try:
                import seed
                seed.main()
                print("[startup] empty database detected -- demo data seeded")
            except Exception as exc:  # never let seeding stop the server booting
                print(f"[startup] seeding skipped: {exc}")

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
