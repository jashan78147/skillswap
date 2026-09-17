"""
routers/admin.py -- the moderation dashboard.

Every endpoint here depends on get_current_admin, so a normal user who
calls them gets 403 Forbidden before any of this code runs.

Covers the four admin requirements from the problem statement:
  1. ban / unban users
  2. moderate spammy skill listings
  3. send platform-wide broadcast messages
  4. download CSV reports
"""

import csv
import io

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_admin
from ..models import Broadcast, Rating, Skill, SwapRequest, User
from ..schemas import AdminStats, BroadcastCreate, BroadcastOut, SkillOut, UserOut

router = APIRouter(prefix="/api/admin", tags=["admin"])

# A second router WITHOUT the admin requirement: every signed-in user
# needs to be able to read broadcasts, they just cannot write them.
public_router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])


# ----------------------------------------------------------------- stats
@router.get("/stats", response_model=AdminStats)
def platform_stats(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    """Headline numbers for the dashboard tiles."""

    def count(model, *conditions):
        stmt = select(func.count(model.id))
        if conditions:
            stmt = stmt.where(*conditions)
        return int(db.scalar(stmt) or 0)

    return AdminStats(
        total_users=count(User),
        banned_users=count(User, User.is_banned.is_(True)),
        total_skills=count(Skill),
        flagged_skills=count(Skill, Skill.is_approved.is_(False)),
        pending_swaps=count(SwapRequest, SwapRequest.status == "pending"),
        accepted_swaps=count(SwapRequest, SwapRequest.status == "accepted"),
        completed_swaps=count(SwapRequest, SwapRequest.status == "completed"),
        total_ratings=count(Rating),
    )


# ------------------------------------------------------------ user admin
@router.get("/users", response_model=list[UserOut])
def list_all_users(
    q: str | None = Query(default=None),
    banned_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Every user, including private and banned ones."""
    stmt = select(User)
    if q:
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(func.lower(User.name).like(needle), func.lower(User.email).like(needle))
        )
    if banned_only:
        stmt = stmt.where(User.is_banned.is_(True))
    return list(db.scalars(stmt.order_by(User.created_at.desc())))


@router.post("/users/{user_id}/ban", response_model=UserOut)
def ban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Suspend an account. The user keeps their data but cannot sign in,
    and disappears from Browse.
    """
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot ban your own account.")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_banned = True

    # Withdraw their open swap requests so nobody is left waiting on
    # a reply from an account that can no longer log in.
    open_swaps = db.scalars(
        select(SwapRequest).where(
            SwapRequest.status == "pending",
            or_(SwapRequest.from_user_id == user_id, SwapRequest.to_user_id == user_id),
        )
    )
    for swap in open_swaps:
        swap.status = "cancelled"

    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/unban", response_model=UserOut)
def unban_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Restore a suspended account."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_banned = False
    db.commit()
    db.refresh(user)
    return user


# ----------------------------------------------------------- skill admin
@router.get("/skills", response_model=list[SkillOut])
def list_all_skills(
    flagged_only: bool = Query(default=False),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Every skill listing on the platform, for moderation review."""
    stmt = select(Skill)
    if flagged_only:
        stmt = stmt.where(Skill.is_approved.is_(False))
    if q:
        stmt = stmt.where(Skill.name_normalized.like(f"%{q.strip().lower()}%"))
    return list(db.scalars(stmt.order_by(Skill.created_at.desc())))


@router.post("/skills/{skill_id}/flag", response_model=SkillOut)
def flag_skill(
    skill_id: int,
    reason: str = Body(default="Violates community guidelines.", embed=True),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Hide a spammy or inappropriate skill listing.

    Deliberately NOT a delete: the row stays, so the decision can be
    reversed and the user does not silently lose their data.
    """
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found.")
    skill.is_approved = False
    skill.rejection_reason = reason.strip() or "Violates community guidelines."
    db.commit()
    db.refresh(skill)
    return skill


@router.post("/skills/{skill_id}/approve", response_model=SkillOut)
def approve_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Restore a previously flagged skill listing."""
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found.")
    skill.is_approved = True
    skill.rejection_reason = None
    db.commit()
    db.refresh(skill)
    return skill


# ------------------------------------------------------------ broadcasts
@router.post("/broadcasts", response_model=BroadcastOut, status_code=status.HTTP_201_CREATED)
def create_broadcast(
    payload: BroadcastCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Post a platform-wide announcement."""
    item = Broadcast(title=payload.title.strip(), body=payload.body.strip())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/broadcasts/{broadcast_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_broadcast(
    broadcast_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    item = db.get(Broadcast, broadcast_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Broadcast not found.")
    db.delete(item)
    db.commit()
    return None


@public_router.get("", response_model=list[BroadcastOut])
def list_broadcasts(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)):
    """Announcements, newest first. Readable by everyone."""
    return list(db.scalars(select(Broadcast).order_by(Broadcast.created_at.desc()).limit(limit)))


# --------------------------------------------------------- CSV reporting
def _csv_response(filename: str, header: list[str], rows: list[list]) -> Response:
    """
    Build a downloadable CSV file in memory.

    StringIO is a "file that lives in memory" -- we write CSV into it,
    then hand the text back with headers that make the browser download
    it instead of displaying it.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/users.csv")
def report_users(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    users = db.scalars(select(User).order_by(User.id))
    rows = [
        [
            u.id, u.name, u.email, u.location or "", u.availability or "",
            "yes" if u.is_public else "no",
            "yes" if u.is_admin else "no",
            "yes" if u.is_banned else "no",
            u.created_at.isoformat(),
        ]
        for u in users
    ]
    return _csv_response(
        "skillswap_users.csv",
        ["id", "name", "email", "location", "availability", "public", "admin", "banned", "joined"],
        rows,
    )


@router.get("/reports/swaps.csv")
def report_swaps(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    swaps = db.scalars(select(SwapRequest).order_by(SwapRequest.id))
    rows = [
        [
            s.id,
            s.from_user.name if s.from_user else "",
            s.to_user.name if s.to_user else "",
            s.offered_skill.name if s.offered_skill else "",
            s.requested_skill.name if s.requested_skill else "",
            s.status,
            s.created_at.isoformat(),
            s.updated_at.isoformat(),
        ]
        for s in swaps
    ]
    return _csv_response(
        "skillswap_swaps.csv",
        ["id", "from", "to", "offered_skill", "requested_skill", "status", "created", "updated"],
        rows,
    )


@router.get("/reports/ratings.csv")
def report_ratings(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    ratings = db.scalars(select(Rating).order_by(Rating.id))
    rows = [
        [
            r.id, r.swap_id,
            r.rater.name if r.rater else "",
            r.ratee.name if r.ratee else "",
            r.stars, (r.comment or "").replace("\n", " "),
            r.created_at.isoformat(),
        ]
        for r in ratings
    ]
    return _csv_response(
        "skillswap_ratings.csv",
        ["id", "swap_id", "rater", "ratee", "stars", "comment", "created"],
        rows,
    )
