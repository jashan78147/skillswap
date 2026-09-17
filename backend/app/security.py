"""
security.py -- passwords and login tokens.

Nothing here talks to the database. These are pure helper functions.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt  # this is the PyJWT library

# ---------------------------------------------------------------------
# The secret key signs your tokens. Anyone who knows it can forge a
# login. For a hackathon demo a hardcoded fallback is fine, but the
# proper way is an environment variable -- which is what this line does:
# "use the SKILLSWAP_SECRET from the environment, or this default."
# ---------------------------------------------------------------------
SECRET_KEY = os.environ.get("SKILLSWAP_SECRET", "dev-secret-change-me-in-production")
ALGORITHM = "HS256"          # the signing method
TOKEN_EXPIRE_HOURS = 24 * 7  # a login lasts one week


# ------------------------------------------------------------ passwords
def hash_password(plain_password: str) -> str:
    """Scramble a password one-way, ready to store in the database."""
    # bcrypt works on raw bytes, not text, so we convert first.
    # It also refuses anything over 72 bytes, so we trim to be safe.
    pw_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Check a typed password against the stored scrambled version."""
    try:
        pw_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(pw_bytes, stored_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash in the database -> treat as "wrong password"
        # rather than crashing the server.
        return False


# --------------------------------------------------------------- tokens
def create_access_token(user_id: int) -> str:
    """
    Build a signed token that says "this is user #<id>".

    'sub' (subject) = who the token is about.
    'exp' (expiry)  = when it stops working.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """
    Verify a token and pull the user id back out.
    Returns None if the token is fake, tampered with, or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id) if user_id is not None else None
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
