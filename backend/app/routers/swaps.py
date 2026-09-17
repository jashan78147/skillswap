"""
routers/swaps.py -- proposing, accepting, rejecting and completing swaps.

The heart of the platform. Most of this file is permission checks:
who is allowed to change a swap, and when.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Rating, Skill, SwapRequest, User
from ..schemas import SwapCreate, SwapOut

router = APIRouter(prefix="/api/swaps", tags=["swaps"])

# Statuses where the two people are considered "connected", so they are
# allowed to see each other contact details.
UNLOCKED_STATUSES = ("accepted", "completed")


def _enrich(db: Session, swap: SwapRequest, viewer: User) -> SwapOut:
    """
    Turn a database row into the richer shape the frontend wants:
    real names instead of bare id numbers, and conditional contact info.
    """
    out = SwapOut.model_validate(swap)

    out.from_user_name = swap.from_user.name if swap.from_user else None
    out.to_user_name = swap.to_user.name if swap.to_user else None
    out.offered_skill_name = swap.offered_skill.name if swap.offered_skill else None
    out.requested_skill_name = swap.requested_skill.name if swap.requested_skill else None

    # Reveal the OTHER person contact details, and only once connected.
    if swap.status in UNLOCKED_STATUSES:
        other = swap.to_user if swap.from_user_id == viewer.id else swap.from_user
        out.contact_info = other.contact_info if other else None

    # Has this viewer already left a rating for this swap?
    out.already_rated = db.scalar(
        select(Rating).where(Rating.swap_id == swap.id, Rating.rater_id == viewer.id)
    ) is not None

    return out


@router.post("", response_model=SwapOut, status_code=status.HTTP_201_CREATED)
def create_swap(
    payload: SwapCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Propose a swap to another user."""
    if payload.to_user_id == current.id:
        raise HTTPException(status_code=400, detail="You cannot send a swap request to yourself.")

    target = db.get(User, payload.to_user_id)
    if target is None or target.is_banned:
        raise HTTPException(status_code=404, detail="That user is not available.")

    # Anti-spam: one open request at a time between the same two people.
    existing = db.scalar(
        select(SwapRequest).where(
            SwapRequest.from_user_id == current.id,
            SwapRequest.to_user_id == target.id,
            SwapRequest.status == "pending",
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending request with this user.",
        )

    # If skills were named, make sure they really belong to the right people.
    if payload.offered_skill_id is not None:
        offered = db.get(Skill, payload.offered_skill_id)
        if offered is None or offered.user_id != current.id:
            raise HTTPException(status_code=400, detail="The offered skill is not one of yours.")

    if payload.requested_skill_id is not None:
        requested = db.get(Skill, payload.requested_skill_id)
        if requested is None or requested.user_id != target.id:
            raise HTTPException(
                status_code=400, detail="The requested skill does not belong to that user."
            )

    swap = SwapRequest(
        from_user_id=current.id,
        to_user_id=target.id,
        offered_skill_id=payload.offered_skill_id,
        requested_skill_id=payload.requested_skill_id,
        message=(payload.message or "").strip() or None,
        status="pending",
    )
    db.add(swap)
    db.commit()
    db.refresh(swap)
    return _enrich(db, swap, current)


@router.get("", response_model=list[SwapOut])
def list_swaps(
    box: str = Query(default="all", description="all | incoming | outgoing"),
    swap_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    Every swap the signed-in user is part of.

    box=incoming -> requests other people sent to me (I can accept/reject)
    box=outgoing -> requests I sent (I can cancel)
    """
    stmt = select(SwapRequest)

    if box == "incoming":
        stmt = stmt.where(SwapRequest.to_user_id == current.id)
    elif box == "outgoing":
        stmt = stmt.where(SwapRequest.from_user_id == current.id)
    else:
        stmt = stmt.where(
            or_(
                SwapRequest.from_user_id == current.id,
                SwapRequest.to_user_id == current.id,
            )
        )

    if swap_status:
        stmt = stmt.where(SwapRequest.status == swap_status)

    swaps = list(db.scalars(stmt.order_by(SwapRequest.created_at.desc())))
    return [_enrich(db, s, current) for s in swaps]


def _load_swap(db: Session, swap_id: int, current: User) -> SwapRequest:
    """Fetch a swap and confirm the signed-in user is actually part of it."""
    swap = db.get(SwapRequest, swap_id)
    if swap is None:
        raise HTTPException(status_code=404, detail="Swap request not found.")
    if current.id not in (swap.from_user_id, swap.to_user_id):
        raise HTTPException(status_code=403, detail="This swap request is not yours.")
    return swap


@router.post("/{swap_id}/accept", response_model=SwapOut)
def accept_swap(
    swap_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Accept a request. Only the RECEIVER may do this."""
    swap = _load_swap(db, swap_id, current)

    if swap.to_user_id != current.id:
        raise HTTPException(
            status_code=403, detail="Only the person who received this request can accept it."
        )
    if swap.status != "pending":
        raise HTTPException(
            status_code=400, detail=f"This request is already {swap.status} and cannot be accepted."
        )

    swap.status = "accepted"
    db.commit()
    db.refresh(swap)
    return _enrich(db, swap, current)


@router.post("/{swap_id}/reject", response_model=SwapOut)
def reject_swap(
    swap_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Decline a request. Only the RECEIVER may do this."""
    swap = _load_swap(db, swap_id, current)

    if swap.to_user_id != current.id:
        raise HTTPException(
            status_code=403, detail="Only the person who received this request can reject it."
        )
    if swap.status != "pending":
        raise HTTPException(
            status_code=400, detail=f"This request is already {swap.status} and cannot be rejected."
        )

    swap.status = "rejected"
    db.commit()
    db.refresh(swap)
    return _enrich(db, swap, current)


@router.post("/{swap_id}/cancel", response_model=SwapOut)
def cancel_swap(
    swap_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Withdraw a request you sent. Only the SENDER may do this, while still pending."""
    swap = _load_swap(db, swap_id, current)

    if swap.from_user_id != current.id:
        raise HTTPException(
            status_code=403, detail="Only the person who sent this request can cancel it."
        )
    if swap.status != "pending":
        raise HTTPException(
            status_code=400, detail=f"This request is already {swap.status} and cannot be cancelled."
        )

    swap.status = "cancelled"
    db.commit()
    db.refresh(swap)
    return _enrich(db, swap, current)


@router.post("/{swap_id}/complete", response_model=SwapOut)
def complete_swap(
    swap_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    Mark an accepted swap as finished. EITHER party may do this,
    and it is what unlocks the ability to leave a rating.
    """
    swap = _load_swap(db, swap_id, current)

    if swap.status != "accepted":
        raise HTTPException(
            status_code=400,
            detail="Only an accepted swap can be marked complete.",
        )

    swap.status = "completed"
    db.commit()
    db.refresh(swap)
    return _enrich(db, swap, current)
