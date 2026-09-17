"""
models.py -- the blueprint of your database tables.

Each class below becomes ONE TABLE.
Each mapped_column becomes ONE COLUMN in that table.

You never write raw database commands. You work with these Python
objects, and SQLAlchemy translates that into database operations.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """
    Current time in UTC, with the timezone label removed.

    Why strip it: SQLite silently drops timezone information, but PostgreSQL
    does not. Storing a plain UTC value means both databases hold exactly the
    same thing, so behaviour never differs between your laptop and the
    deployed site.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------- users
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # --- login details ---
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    # NOTE: we store a scrambled hash, never the real password.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # --- public profile ---
    location: Mapped[str | None] = mapped_column(String(160), default=None)
    bio: Mapped[str | None] = mapped_column(Text, default=None)
    availability: Mapped[str | None] = mapped_column(String(200), default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(500), default=None)

    # --- PRIVATE: only revealed once a swap is ACCEPTED ---
    contact_info: Mapped[str | None] = mapped_column(String(255), default=None)

    # --- flags ---
    # is_public=False hides this profile from the Browse page entirely.
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    # "relationship" is a convenience: user.skills gives you that user's
    # skill rows without you writing a lookup by hand.
    # cascade="all, delete-orphan" => deleting a user deletes their skills too.
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# --------------------------------------------------------------- skills
class Skill(Base):
    """
    One row = one skill belonging to one user.

    kind == "offered"  -> a skill this user can teach
    kind == "wanted"   -> a skill this user wants to learn

    Keeping both in one table (instead of two) means the search code
    is written once and works for both directions.
    """
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    # Lowercased copy of `name`, used for case-insensitive search and matching.
    name_normalized: Mapped[str] = mapped_column(String(120), index=True, nullable=False)

    kind: Mapped[str] = mapped_column(String(10), nullable=False)          # offered | wanted
    level: Mapped[str] = mapped_column(String(20), default="intermediate") # beginner | intermediate | expert
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # Admin moderation: an admin can flag a spammy listing, which hides it
    # from Browse without deleting the user's data.
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="skills")


# -------------------------------------------------------- swap requests
class SwapRequest(Base):
    """
    One row = one swap proposal between two users.

    status flows:
        pending  --accept-->  accepted  --complete-->  completed
        pending  --reject-->  rejected
        pending  --cancel-->  cancelled   (only the sender may cancel)
    """
    __tablename__ = "swap_requests"

    id: Mapped[int] = mapped_column(primary_key=True)

    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    # Which skill the sender offers, and which they want in return.
    offered_skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id"), default=None)
    requested_skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id"), default=None)

    message: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # foreign_keys= is required here because this table points at users.id TWICE,
    # so SQLAlchemy needs to be told which column feeds which relationship.
    from_user: Mapped["User"] = relationship(foreign_keys=[from_user_id])
    to_user: Mapped["User"] = relationship(foreign_keys=[to_user_id])
    offered_skill: Mapped["Skill | None"] = relationship(foreign_keys=[offered_skill_id])
    requested_skill: Mapped["Skill | None"] = relationship(foreign_keys=[requested_skill_id])


# -------------------------------------------------------------- ratings
class Rating(Base):
    """A star rating + comment, left after a swap is marked completed."""
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(primary_key=True)

    swap_id: Mapped[int] = mapped_column(ForeignKey("swap_requests.id"), index=True, nullable=False)
    rater_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)  # who wrote it
    ratee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)  # who it's about

    stars: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5
    comment: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    rater: Mapped["User"] = relationship(foreign_keys=[rater_id])
    ratee: Mapped["User"] = relationship(foreign_keys=[ratee_id])


# ----------------------------------------------------------- broadcasts
class Broadcast(Base):
    """Platform-wide announcement written by an admin."""
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
