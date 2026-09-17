"""
routers/auth.py -- signing up, signing in, and "who am I?".
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, SignupIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

# Every URL in this file automatically starts with /api/auth
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    """
    Create a new account.

    `payload` arrives already validated by Pydantic -- if the email was
    malformed or the password under 6 characters, we never get here.
    """
    # Store emails lowercased so "Bob@x.com" and "bob@x.com" are one account.
    email = payload.email.strip().lower()

    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use",
        )

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )

    # The first account ever created becomes the admin, so you always
    # have a way into the admin panel on a fresh database.
    if db.scalar(select(User).limit(1)) is None:
        user.is_admin = True

    db.add(user)      # stage it
    db.commit()       # actually write to the file
    db.refresh(user)  # reload so user.id is populated

    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """Exchange an email + password for a token."""
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    # Deliberately the SAME message whether the email is unknown or the
    # password is wrong. Saying "no such email" would let a stranger
    # discover which addresses are registered.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been suspended by an administrator.",
        )

    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    """
    Return the signed-in user's own profile.

    The frontend calls this when the page reloads: it still has the
    token saved, and needs to turn that back into user details.
    """
    return current
