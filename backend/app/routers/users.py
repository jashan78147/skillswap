"""
routers/users.py -- your own profile, plus browsing and searching others.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..models import Rating, Skill, SwapRequest, User
from ..schemas import ProfileUpdate, SkillOut, UserOut, UserPublic

router = APIRouter(prefix="/api/users", tags=["users"])


# --------------------------------------------------------------- helpers
def _contact_unlocked(db: Session, viewer: User | None, target_id: int) -> bool:
    """
    Contact details are private until a swap between these two people
    has been ACCEPTED. This is the privacy rule from the spec.
    """
    if viewer is None:
        return False
    if viewer.id == target_id:
        return True  # you can always see your own
    if viewer.is_admin:
        return True  # admins can see everything for moderation

    swap = db.scalar(
        select(SwapRequest).where(
            SwapRequest.status.in_(["accepted", "completed"]),
            or_(
                (SwapRequest.from_user_id == viewer.id) & (SwapRequest.to_user_id == target_id),
                (SwapRequest.from_user_id == target_id) & (SwapRequest.to_user_id == viewer.id),
            ),
        )
    )
    return swap is not None


def _rating_summary(db: Session, user_id: int) -> tuple[float | None, int]:
    """Average stars and how many ratings this user has received."""
    row = db.execute(
        select(func.avg(Rating.stars), func.count(Rating.id)).where(Rating.ratee_id == user_id)
    ).one()
    average, count = row
    return (round(float(average), 2) if average is not None else None, int(count or 0))


def build_public_profile(db: Session, user: User, viewer: User | None) -> UserPublic:
    """Assemble the version of a profile that other people are allowed to see."""
    skills = list(
        db.scalars(
            select(Skill).where(Skill.user_id == user.id, Skill.is_approved.is_(True))
        )
    )
    average, count = _rating_summary(db, user.id)

    profile = UserPublic.model_validate(user)
    profile.skills_offered = [SkillOut.model_validate(s) for s in skills if s.kind == "offered"]
    profile.skills_wanted = [SkillOut.model_validate(s) for s in skills if s.kind == "wanted"]
    profile.average_rating = average
    profile.rating_count = count
    profile.contact_info = user.contact_info if _contact_unlocked(db, viewer, user.id) else None
    return profile


# ------------------------------------------------------------ my profile
@router.get("/me", response_model=UserOut)
def get_my_profile(current: User = Depends(get_current_user)):
    return current


@router.patch("/me", response_model=UserOut)
def update_my_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    Update only the fields that were actually sent.

    exclude_unset=True is the important part: it gives us just the keys
    the browser included, so omitting 'bio' leaves the existing bio
    alone instead of wiping it to null.
    """
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(current, field, value)

    db.commit()
    db.refresh(current)
    return current


# ---------------------------------------------------------------- browse
@router.get("/browse", response_model=dict)
def browse_users(
    q: str | None = Query(default=None, description="Search name, skill, location or bio"),
    skill: str | None = Query(default=None, description="Filter by one exact skill name"),
    level: str | None = Query(default=None, description="beginner | intermediate | expert"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    """
    The public directory of swappers.

    Hidden from results: banned users, users who set their profile to
    private, and the viewer themselves.
    """
    stmt = select(User).where(User.is_banned.is_(False), User.is_public.is_(True))
    if viewer is not None:
        stmt = stmt.where(User.id != viewer.id)

    # --- free text search across name, location, bio and skill names ---
    if q:
        needle = f"%{q.strip().lower()}%"
        matching_user_ids = select(Skill.user_id).where(
            Skill.name_normalized.like(needle), Skill.is_approved.is_(True)
        )
        stmt = stmt.where(
            or_(
                func.lower(User.name).like(needle),
                func.lower(func.coalesce(User.location, "")).like(needle),
                func.lower(func.coalesce(User.bio, "")).like(needle),
                User.id.in_(matching_user_ids),
            )
        )

    # --- filter to people offering one specific skill ---
    if skill:
        skill_filter = select(Skill.user_id).where(
            Skill.name_normalized == skill.strip().lower(),
            Skill.kind == "offered",
            Skill.is_approved.is_(True),
        )
        if level:
            skill_filter = skill_filter.where(Skill.level == level)
        stmt = stmt.where(User.id.in_(skill_filter))

    # Count the full result set BEFORE slicing, so the frontend can
    # show "showing 12 of 47".
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    users = list(
        db.scalars(
            stmt.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page * page_size) < total,
        "results": [build_public_profile(db, u, viewer) for u in users],
    }


@router.get("/{user_id}", response_model=UserPublic)
def get_public_profile(
    user_id: int,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    """One person's public profile page."""
    user = db.get(User, user_id)
    if user is None or user.is_banned:
        raise HTTPException(status_code=404, detail="User not found.")

    # A private profile is still visible to its owner and to admins.
    is_self = viewer is not None and viewer.id == user.id
    is_admin = viewer is not None and viewer.is_admin
    if not user.is_public and not is_self and not is_admin:
        raise HTTPException(status_code=403, detail="This profile is private.")

    return build_public_profile(db, user, viewer)
