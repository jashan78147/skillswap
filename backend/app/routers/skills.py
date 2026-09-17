"""
routers/skills.py -- add, view, edit and remove your own skills.

Every endpoint here requires a login, and every one only ever touches
skills belonging to the signed-in user.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Skill, SwapRequest, User
from ..schemas import SkillCreate, SkillOut

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.post("", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
def add_skill(
    payload: SkillCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Add a skill you can teach ("offered") or want to learn ("wanted")."""
    clean_name = payload.name.strip()
    normalized = clean_name.lower()

    if not clean_name:
        raise HTTPException(status_code=422, detail="Skill name cannot be empty.")

    # Block the same skill twice in the same direction, so a user cannot
    # spam "Python" ten times to game the search results.
    duplicate = db.scalar(
        select(Skill).where(
            Skill.user_id == current.id,
            Skill.name_normalized == normalized,
            Skill.kind == payload.kind,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{clean_name}' is already in your {payload.kind} list.",
        )

    skill = Skill(
        user_id=current.id,
        name=clean_name,
        name_normalized=normalized,
        kind=payload.kind,
        level=payload.level,
        description=(payload.description or "").strip() or None,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/me", response_model=list[SkillOut])
def my_skills(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """All of the signed-in user's skills, newest first."""
    return list(
        db.scalars(
            select(Skill)
            .where(Skill.user_id == current.id)
            .order_by(Skill.created_at.desc())
        )
    )


@router.patch("/{skill_id}", response_model=SkillOut)
def update_skill(
    skill_id: int,
    payload: SkillCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Edit one of your own skills."""
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found.")

    # The ownership check. Without this, anyone could edit anyone's
    # skills just by guessing an id number.
    if skill.user_id != current.id:
        raise HTTPException(status_code=403, detail="That skill is not yours to edit.")

    skill.name = payload.name.strip()
    skill.name_normalized = skill.name.lower()
    skill.kind = payload.kind
    skill.level = payload.level
    skill.description = (payload.description or "").strip() or None

    # Editing a skill an admin had flagged puts it back under review.
    if not skill.is_approved:
        skill.is_approved = True
        skill.rejection_reason = None

    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Remove one of your own skills."""
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found.")
    if skill.user_id != current.id:
        raise HTTPException(status_code=403, detail="That skill is not yours to delete.")

    # Past swap requests may point at this skill. Deleting the row without
    # clearing those references leaves them pointing at nothing, and the
    # swap silently loses the record of what it was about.
    db.query(SwapRequest).filter(SwapRequest.offered_skill_id == skill_id).update(
        {"offered_skill_id": None}, synchronize_session=False
    )
    db.query(SwapRequest).filter(SwapRequest.requested_skill_id == skill_id).update(
        {"requested_skill_id": None}, synchronize_session=False
    )

    db.delete(skill)
    db.commit()
    # 204 means "success, and there is deliberately nothing to send back".
    return None


@router.get("/popular", response_model=list[dict])
def popular_skills(limit: int = 20, db: Session = Depends(get_db)):
    """
    The most commonly offered skills across the platform.
    The frontend uses this for suggestion chips on the browse page.
    """
    rows = db.execute(
        select(Skill.name, func.count(Skill.id).label("count"))
        .where(Skill.kind == "offered", Skill.is_approved.is_(True))
        .group_by(Skill.name_normalized)
        .order_by(func.count(Skill.id).desc())
        .limit(limit)
    ).all()
    return [{"name": name, "count": count} for name, count in rows]
