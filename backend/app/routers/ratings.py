"""
routers/ratings.py -- star ratings and written feedback after a swap.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Rating, SwapRequest, User
from ..schemas import RatingCreate, RatingOut

router = APIRouter(prefix="/api/ratings", tags=["ratings"])


def _decorate(rating: Rating) -> RatingOut:
    """Attach readable names so the frontend does not need extra lookups."""
    out = RatingOut.model_validate(rating)
    out.rater_name = rating.rater.name if rating.rater else None
    out.ratee_name = rating.ratee.name if rating.ratee else None
    return out


@router.post("", response_model=RatingOut, status_code=status.HTTP_201_CREATED)
def leave_rating(
    payload: RatingCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Rate the other person in a completed swap."""
    swap = db.get(SwapRequest, payload.swap_id)
    if swap is None:
        raise HTTPException(status_code=404, detail="Swap request not found.")

    # Rule 1: you must have been part of this swap.
    if current.id not in (swap.from_user_id, swap.to_user_id):
        raise HTTPException(status_code=403, detail="You were not part of this swap.")

    # Rule 2: only finished swaps can be rated.
    if swap.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="You can only leave a rating once the swap is marked complete.",
        )

    # Rule 3: one rating per person per swap.
    already = db.scalar(
        select(Rating).where(Rating.swap_id == swap.id, Rating.rater_id == current.id)
    )
    if already is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already rated this swap.",
        )

    # Work out who is being rated: whichever side of the swap is not me.
    # Derived on the server, so it cannot be faked by the browser.
    ratee_id = swap.to_user_id if swap.from_user_id == current.id else swap.from_user_id

    rating = Rating(
        swap_id=swap.id,
        rater_id=current.id,
        ratee_id=ratee_id,
        stars=payload.stars,
        comment=(payload.comment or "").strip() or None,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return _decorate(rating)


@router.get("/me", response_model=list[RatingOut])
def ratings_about_me(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Ratings other people have left about the signed-in user."""
    rows = db.scalars(
        select(Rating).where(Rating.ratee_id == current.id).order_by(Rating.created_at.desc())
    )
    return [_decorate(r) for r in rows]


@router.get("/given", response_model=list[RatingOut])
def ratings_i_wrote(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Ratings the signed-in user has written about others."""
    rows = db.scalars(
        select(Rating).where(Rating.rater_id == current.id).order_by(Rating.created_at.desc())
    )
    return [_decorate(r) for r in rows]


@router.get("/user/{user_id}", response_model=dict)
def ratings_for_user(user_id: int, db: Session = Depends(get_db)):
    """
    Public reputation for one user: the average, the count, and the
    individual reviews. Used on profile pages.
    """
    target = db.get(User, user_id)
    if target is None or target.is_banned:
        raise HTTPException(status_code=404, detail="User not found.")

    average, count = db.execute(
        select(func.avg(Rating.stars), func.count(Rating.id)).where(Rating.ratee_id == user_id)
    ).one()

    rows = db.scalars(
        select(Rating).where(Rating.ratee_id == user_id).order_by(Rating.created_at.desc())
    )

    return {
        "user_id": user_id,
        "user_name": target.name,
        "average_rating": round(float(average), 2) if average is not None else None,
        "rating_count": int(count or 0),
        "ratings": [_decorate(r).model_dump() for r in rows],
    }
