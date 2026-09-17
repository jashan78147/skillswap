"""
main.py -- the entry point. Running the server runs this file.

Responsibilities:
  1. Create the FastAPI application
  2. Allow the React frontend to talk to it (CORS)
  3. Make sure the database tables exist
  4. Plug in the routers that define the actual URLs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models  # noqa: F401  -- importing registers the tables
from app.routers import admin, auth, matches, ratings, skills, swaps, users

# ---------------------------------------------------------------------
# Build any missing tables on startup, so a fresh clone of this project
# runs with no setup step.
# ---------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SkillSwap API",
    description="Peer-to-peer skill exchange platform.",
    version="1.0.0",
)

# ---------------------------------------------------------------------
# CORS: which web addresses are allowed to call this API.
# 5173 is Vite's default port, 3000 is a common alternative.
# ---------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    # Vite normally uses 5173, but if that port is busy it silently moves to
    # 5174, 5175 and so on. Listing a few spares means the app keeps working
    # instead of failing with a confusing CORS error mid-demo.
    allow_origins=[
        "http://localhost:5173",  "http://127.0.0.1:5173",
        "http://localhost:5174",  "http://127.0.0.1:5174",
        "http://localhost:5175",  "http://127.0.0.1:5175",
        "http://localhost:3000",  "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PATCH, DELETE ...
    allow_headers=["*"],   # including our Authorization header
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
    Handy for confirming the server is up without testing real logic.
    """
    return {"status": "ok", "service": "SkillSwap API"}
