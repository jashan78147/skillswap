"""
deps.py -- reusable "who is asking?" checks.

FastAPI calls these BEFORE running an endpoint. If one raises an
error, the endpoint never runs at all.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_access_token

# Tells FastAPI to look for a header shaped like:
#     Authorization: Bearer <token>
# auto_error=False lets US write the error message instead of FastAPI.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Turn the token in the request header into a real User row.
    Raises 401 (Unauthorized) if anything is wrong.
    """
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not signed in.",
        )

    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or has expired. Please sign in again.",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account no longer exists.",
        )

    # A banned user may hold a valid token, but is refused here.
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been suspended by an administrator.",
        )

    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """
    Same as above, plus an admin check.
    Note it DEPENDS ON get_current_user -- dependencies can chain.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return user


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """
    For pages that work signed-out but show extra detail when signed in.
    Returns None instead of raising.
    """
    if creds is None:
        return None
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or user.is_banned:
        return None
    return user
