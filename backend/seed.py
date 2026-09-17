"""
seed.py -- fill the database with realistic demo data.

Run it with:
    venv\\Scripts\\python.exe seed.py

Safe to run more than once: it skips anything that already exists.
Your own admin account is never touched.

Why this matters for a hackathon: an empty app demos badly. Judges
cannot tell whether search, matching or ratings work when there is
nothing to search. This gives you a populated, believable platform
in two seconds.
"""

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Broadcast, Rating, Skill, SwapRequest, User
from app.security import hash_password

DEMO_PASSWORD = "demo123"

# (name, email, location, availability, bio, [offered], [wanted])
PEOPLE = [
    (
        "Maria Lopez", "maria@skillswap.com", "Oakland, California",
        "Weekends and evenings",
        "Native Spanish speaker, learning frontend development.",
        [("Spanish Conversation", "expert"), ("Salsa Dancing", "intermediate")],
        [("React / Frontend", "beginner"), ("Photography", "beginner")],
    ),
    (
        "Arjun Mehta", "arjun@skillswap.com", "Jalandhar, Punjab",
        "Weekday evenings",
        "Backend engineer. Happy to trade API design for design skills.",
        [("Node.js API", "expert"), ("Python", "expert")],
        [("UI / UX Design", "beginner"), ("Public Speaking", "intermediate")],
    ),
    (
        "Sneha Kapoor", "sneha@skillswap.com", "Jalandhar, Punjab",
        "Weekends",
        "Product designer who wants to understand the code side.",
        [("UI / UX Design", "expert"), ("Figma", "expert")],
        [("Python", "beginner"), ("Node.js API", "beginner")],
    ),
    (
        "Daniel Okafor", "daniel@skillswap.com", "Berlin, Germany",
        "Flexible",
        "Photographer and part-time guitar teacher.",
        [("Photography", "expert"), ("Guitar", "intermediate")],
        [("Spanish Conversation", "beginner"), ("Video Editing", "beginner")],
    ),
    (
        "Yuki Tanaka", "yuki@skillswap.com", "Tokyo, Japan",
        "Early mornings",
        "Data analyst. Learning to speak in front of an audience.",
        [("Data Analysis", "expert"), ("Excel / Spreadsheets", "expert")],
        [("Public Speaking", "beginner"), ("Guitar", "beginner")],
    ),
    (
        "Priya Sharma", "priya@skillswap.com", "Jalandhar, Punjab",
        "Weekday afternoons",
        "Communications coach. Always wanted to learn to code.",
        [("Public Speaking", "expert"), ("Content Writing", "expert")],
        [("React / Frontend", "beginner"), ("Data Analysis", "beginner")],
    ),
    (
        "Tom Becker", "tom@skillswap.com", "Berlin, Germany",
        "Weekends",
        "Video editor looking to pick up design fundamentals.",
        [("Video Editing", "expert"), ("Motion Graphics", "intermediate")],
        [("Figma", "beginner"), ("Photography", "intermediate")],
    ),
]


def main() -> None:
    db = SessionLocal()
    created_users = 0
    created_skills = 0

    for name, email, location, availability, bio, offered, wanted in PEOPLE:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                name=name,
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                location=location,
                availability=availability,
                bio=bio,
                contact_info=f"{email} | +1-555-{abs(hash(email)) % 9000 + 1000}",
                is_public=True,
            )
            db.add(user)
            db.flush()          # assigns user.id without a full commit
            created_users += 1

        for skill_name, level in offered:
            exists = db.scalar(
                select(Skill).where(
                    Skill.user_id == user.id,
                    Skill.name_normalized == skill_name.lower(),
                    Skill.kind == "offered",
                )
            )
            if exists is None:
                db.add(Skill(
                    user_id=user.id, name=skill_name,
                    name_normalized=skill_name.lower(),
                    kind="offered", level=level,
                ))
                created_skills += 1

        for skill_name, level in wanted:
            exists = db.scalar(
                select(Skill).where(
                    Skill.user_id == user.id,
                    Skill.name_normalized == skill_name.lower(),
                    Skill.kind == "wanted",
                )
            )
            if exists is None:
                db.add(Skill(
                    user_id=user.id, name=skill_name,
                    name_normalized=skill_name.lower(),
                    kind="wanted", level=level,
                ))
                created_skills += 1

    db.commit()

    # ---------------------------------------------------------------
    # A few swaps in different states, so the Requests page has
    # something in every tab during the demo.
    # ---------------------------------------------------------------
    def user_by(email: str) -> User | None:
        return db.scalar(select(User).where(User.email == email))

    arjun, sneha = user_by("arjun@skillswap.com"), user_by("sneha@skillswap.com")
    daniel, yuki = user_by("daniel@skillswap.com"), user_by("yuki@skillswap.com")
    priya, tom = user_by("priya@skillswap.com"), user_by("tom@skillswap.com")

    def make_swap(sender, receiver, status):
        if sender is None or receiver is None:
            return None
        existing = db.scalar(
            select(SwapRequest).where(
                SwapRequest.from_user_id == sender.id,
                SwapRequest.to_user_id == receiver.id,
            )
        )
        if existing is not None:
            return existing
        offered = db.scalar(
            select(Skill).where(Skill.user_id == sender.id, Skill.kind == "offered")
        )
        requested = db.scalar(
            select(Skill).where(Skill.user_id == receiver.id, Skill.kind == "offered")
        )
        swap = SwapRequest(
            from_user_id=sender.id, to_user_id=receiver.id,
            offered_skill_id=offered.id if offered else None,
            requested_skill_id=requested.id if requested else None,
            message=f"Hi {receiver.name.split()[0]}, would you like to swap?",
            status=status,
        )
        db.add(swap)
        db.flush()
        return swap

    make_swap(arjun, sneha, "completed")
    make_swap(sneha, yuki, "accepted")
    make_swap(daniel, tom, "pending")
    make_swap(priya, yuki, "rejected")
    db.commit()

    # Ratings on the completed swap only -- the rules require it.
    done = db.scalar(select(SwapRequest).where(SwapRequest.status == "completed"))
    if done is not None:
        for rater_id, ratee_id, stars, comment in [
            (done.from_user_id, done.to_user_id, 5, "Explained everything clearly. Great swap."),
            (done.to_user_id, done.from_user_id, 4, "Very patient and well prepared."),
        ]:
            exists = db.scalar(
                select(Rating).where(Rating.swap_id == done.id, Rating.rater_id == rater_id)
            )
            if exists is None:
                db.add(Rating(
                    swap_id=done.id, rater_id=rater_id, ratee_id=ratee_id,
                    stars=stars, comment=comment,
                ))

    if db.scalar(select(Broadcast)) is None:
        db.add(Broadcast(
            title="Welcome to SkillSwap",
            body="Add at least one skill you can offer and one you want to learn "
                 "to start getting match suggestions.",
        ))

    db.commit()

    print(f"  users created:  {created_users}")
    print(f"  skills created: {created_skills}")
    print(f"  total users:    {db.query(User).count()}")
    print(f"  total skills:   {db.query(Skill).count()}")
    print(f"  total swaps:    {db.query(SwapRequest).count()}")
    print(f"  total ratings:  {db.query(Rating).count()}")
    print(f"\n  demo accounts all use the password: {DEMO_PASSWORD}")
    db.close()


if __name__ == "__main__":
    main()
