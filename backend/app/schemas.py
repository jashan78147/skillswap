"""
schemas.py -- the shape of data travelling IN and OUT of the API.

Different from models.py on purpose:
  models.py  = what is STORED    (includes password_hash)
  schemas.py = what is SENT      (never includes password_hash)

Naming convention used here:
  ...Create  -> data the browser sends to make something
  ...Update  -> data the browser sends to change something
  ...Out     -> data the server sends back
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Tells Pydantic it is allowed to read values off SQLAlchemy objects
# (not just plain dictionaries). Needed on every "Out" schema.
ORM = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------- auth
class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# --------------------------------------------------------------- skills
SkillKind = Literal["offered", "wanted"]
SkillLevel = Literal["beginner", "intermediate", "expert"]


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: SkillKind
    level: SkillLevel = "intermediate"
    description: str | None = Field(default=None, max_length=1000)


class SkillOut(BaseModel):
    model_config = ORM

    id: int
    user_id: int
    name: str
    kind: str
    level: str
    description: str | None
    is_approved: bool
    rejection_reason: str | None
    created_at: datetime


# ---------------------------------------------------------------- users
class ProfileUpdate(BaseModel):
    """Every field optional -- send only what you want to change."""
    name: str | None = Field(default=None, min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=2000)
    availability: str | None = Field(default=None, max_length=200)
    avatar_url: str | None = Field(default=None, max_length=500)
    contact_info: str | None = Field(default=None, max_length=255)
    is_public: bool | None = None


class UserOut(BaseModel):
    """The full view -- only ever sent to the user about themselves."""
    model_config = ORM

    id: int
    name: str
    email: EmailStr
    location: str | None
    bio: str | None
    availability: str | None
    avatar_url: str | None
    contact_info: str | None
    is_public: bool
    is_admin: bool
    is_banned: bool
    created_at: datetime


class UserPublic(BaseModel):
    """
    The view OTHER people get. Note what is missing: email, and
    contact_info is only filled in once a swap has been accepted.
    """
    model_config = ORM

    id: int
    name: str
    location: str | None
    bio: str | None
    availability: str | None
    avatar_url: str | None
    created_at: datetime

    # computed / conditional fields, filled in by the endpoint code
    skills_offered: list[SkillOut] = []
    skills_wanted: list[SkillOut] = []
    average_rating: float | None = None
    rating_count: int = 0
    contact_info: str | None = None  # None unless unlocked by an accepted swap


# ----------------------------------------------------------------- swaps
SwapStatus = Literal["pending", "accepted", "rejected", "cancelled", "completed"]


class SwapCreate(BaseModel):
    to_user_id: int
    offered_skill_id: int | None = None
    requested_skill_id: int | None = None
    message: str | None = Field(default=None, max_length=1000)


class SwapOut(BaseModel):
    model_config = ORM

    id: int
    from_user_id: int
    to_user_id: int
    offered_skill_id: int | None
    requested_skill_id: int | None
    message: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    # friendly extras so the frontend does not need extra lookups
    from_user_name: str | None = None
    to_user_name: str | None = None
    offered_skill_name: str | None = None
    requested_skill_name: str | None = None
    contact_info: str | None = None   # unlocked only when status == accepted
    already_rated: bool = False


# --------------------------------------------------------------- ratings
class RatingCreate(BaseModel):
    swap_id: int
    stars: int = Field(ge=1, le=5)   # ge = at least, le = at most
    comment: str | None = Field(default=None, max_length=1000)


class RatingOut(BaseModel):
    model_config = ORM

    id: int
    swap_id: int
    rater_id: int
    ratee_id: int
    stars: int
    comment: str | None
    created_at: datetime

    rater_name: str | None = None
    ratee_name: str | None = None


# --------------------------------------------------------------- matches
class MatchOut(BaseModel):
    """One suggested swap partner, produced by the matching algorithm."""
    user: UserPublic
    score: float
    they_teach_you: list[str] = []   # skills they offer that you want
    you_teach_them: list[str] = []   # skills you offer that they want
    is_mutual: bool = False          # True when BOTH directions line up
    reason: str = ""


# ------------------------------------------------------------ broadcasts
class BroadcastCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


class BroadcastOut(BaseModel):
    model_config = ORM

    id: int
    title: str
    body: str
    created_at: datetime


# --------------------------------------------------------------- admin
class AdminStats(BaseModel):
    total_users: int
    banned_users: int
    total_skills: int
    flagged_skills: int
    pending_swaps: int
    accepted_swaps: int
    completed_swaps: int
    total_ratings: int


# Resolves the forward reference to UserOut used inside TokenOut above.
TokenOut.model_rebuild()
