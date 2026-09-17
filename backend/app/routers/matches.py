"""
routers/matches.py -- smart match suggestions.

Finds the people you are most likely to swap with, using skill-overlap
arithmetic. No external AI service, no API key, no network call:
it runs locally in milliseconds and gives identical results every time,
which is exactly what you want during a live demo.

The core idea is the "double coincidence of wants": a swap only works
when THEY teach what YOU want AND YOU teach what THEY want. Matches
that work in both directions score far higher than one-way ones.
"""

import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Rating, Skill, SwapRequest, User
from ..schemas import MatchOut
from .users import build_public_profile

router = APIRouter(prefix="/api/matches", tags=["matches"])

# Words that carry no meaning when comparing skill names, so they are
# ignored. Without this, "Web Design" and "Web Development" would look
# more similar than they really are.
STOPWORDS = {"and", "or", "the", "a", "an", "of", "for", "with", "in", "to", "basics", "intro"}

# How much two skill names must overlap to count as the same skill.
# 0.5 means "React" matches "React / Frontend" (1 shared word out of 2).
SIMILARITY_THRESHOLD = 0.5


def tokenize(skill_name: str) -> set[str]:
    """
    Break a skill name into a set of meaningful lowercase words.

        "React / Frontend"  ->  {"react", "frontend"}
        "Spanish Conversation" -> {"spanish", "conversation"}
    """
    words = re.split(r"[^a-z0-9+#]+", skill_name.lower())
    return {w for w in words if w and w not in STOPWORDS}


def similarity(a: str, b: str) -> float:
    """
    How alike are two skill names, from 0.0 (nothing in common)
    to 1.0 (identical)?

    Exact text match is an instant 1.0. Otherwise we compare word sets:
    shared words divided by the size of the larger set.
    """
    if a.strip().lower() == b.strip().lower():
        return 1.0

    tokens_a, tokens_b = tokenize(a), tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0

    shared = tokens_a & tokens_b
    if not shared:
        return 0.0

    return len(shared) / max(len(tokens_a), len(tokens_b))


def overlapping_skills(supply: list[Skill], demand: list[Skill]) -> list[str]:
    """
    Which skills in `supply` satisfy something in `demand`?

    Used twice per candidate: once for what they can teach you,
    once for what you can teach them.
    """
    hits: list[str] = []
    for offered in supply:
        for wanted in demand:
            if similarity(offered.name, wanted.name) >= SIMILARITY_THRESHOLD:
                hits.append(offered.name)
                break  # counted once, move to the next offered skill
    return hits


@router.get("", response_model=list[MatchOut])
def suggested_matches(
    limit: int = Query(default=10, ge=1, le=50),
    exclude_existing: bool = Query(
        default=True, description="Hide people you already have a swap with"
    ),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    Ranked swap partners for the signed-in user.

    Anyone scoring zero is left out entirely, so the page never shows
    irrelevant suggestions just to fill space.
    """
    # --- what I offer and what I want ---
    my_skills = list(
        db.scalars(select(Skill).where(Skill.user_id == current.id, Skill.is_approved.is_(True)))
    )
    my_offered = [s for s in my_skills if s.kind == "offered"]
    my_wanted = [s for s in my_skills if s.kind == "wanted"]

    # Nothing to match on yet -> return empty rather than random people.
    if not my_offered and not my_wanted:
        return []

    # --- people to skip ---
    skip_ids = {current.id}
    if exclude_existing:
        existing = db.scalars(
            select(SwapRequest).where(
                SwapRequest.status.in_(["pending", "accepted", "completed"])
            )
        )
        for swap in existing:
            if swap.from_user_id == current.id:
                skip_ids.add(swap.to_user_id)
            elif swap.to_user_id == current.id:
                skip_ids.add(swap.from_user_id)

    candidates = list(
        db.scalars(
            select(User).where(
                User.is_banned.is_(False),
                User.is_public.is_(True),
                User.id.notin_(skip_ids),
            )
        )
    )

    results: list[MatchOut] = []

    for person in candidates:
        their_skills = list(
            db.scalars(
                select(Skill).where(Skill.user_id == person.id, Skill.is_approved.is_(True))
            )
        )
        their_offered = [s for s in their_skills if s.kind == "offered"]
        their_wanted = [s for s in their_skills if s.kind == "wanted"]

        they_teach_you = overlapping_skills(their_offered, my_wanted)
        you_teach_them = overlapping_skills(my_offered, their_wanted)

        # No overlap in either direction -> not a match at all.
        if not they_teach_you and not you_teach_them:
            continue

        is_mutual = bool(they_teach_you) and bool(you_teach_them)

        # ---------------- scoring ----------------
        score = 0.0

        # The big one: a swap that works BOTH ways.
        if is_mutual:
            score += 40.0

        # Breadth of overlap, capped so one person with 20 skills
        # cannot dominate the rankings.
        score += min(len(they_teach_you), 3) * 12.0
        score += min(len(you_teach_them), 3) * 8.0

        # Same city is genuinely useful for in-person swaps.
        if (
            current.location
            and person.location
            and current.location.strip().lower() == person.location.strip().lower()
        ):
            score += 6.0

        # A small nudge towards people with good feedback.
        avg_stars = db.scalar(
            select(func.avg(Rating.stars)).where(Rating.ratee_id == person.id)
        )
        if avg_stars is not None:
            score += (float(avg_stars) / 5.0) * 8.0

        score = round(min(score, 100.0), 1)

        # ---------------- plain-English reason ----------------
        if is_mutual:
            reason = (
                f"Perfect two-way match: {person.name} can teach you "
                f"{they_teach_you[0]}, and you can teach them {you_teach_them[0]}."
            )
        elif they_teach_you:
            reason = f"{person.name} offers {they_teach_you[0]}, which is on your learning list."
        else:
            reason = f"{person.name} wants to learn {you_teach_them[0]}, which you offer."

        results.append(
            MatchOut(
                user=build_public_profile(db, person, current),
                score=score,
                they_teach_you=they_teach_you,
                you_teach_them=you_teach_them,
                is_mutual=is_mutual,
                reason=reason,
            )
        )

    # Best first, then cut to the requested number.
    results.sort(key=lambda m: m.score, reverse=True)
    return results[:limit]
