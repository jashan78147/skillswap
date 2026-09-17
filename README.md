# SkillSwap

A peer-to-peer skill exchange platform. People list what they can teach and
what they want to learn, find each other, propose a swap, and rate each other
once it is done. No money changes hands — skills are traded directly.

Built for the Odoo x LPU Jalandhar Hackathon.

---

## What it does

**For everyone**

- Sign up, sign in, and manage a profile (location, bio, availability, photo)
- List skills you **offer** and skills you **want**, each with a level
- Browse and search everyone by name, skill, city or bio, with pagination
- Set your profile **public or private**
- Get **smart match suggestions** ranked by how well your skills line up
- Send, accept, reject, cancel and complete swap requests
- Rate the other person once a swap is complete, and build a public reputation

**Privacy**

Contact details stay hidden until a swap between two people is **accepted**.
The check runs on the server, so it cannot be bypassed from the browser.

**For admins**

- Ban and reinstate users (pending requests are withdrawn automatically)
- Hide spammy or inappropriate skill listings, with a reason, without
  deleting the user's data
- Publish platform-wide announcements
- Download CSV reports of users, swaps and ratings

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (Python) | Fast to write, and generates interactive API docs for free |
| Database | SQLite + SQLAlchemy | Zero setup, one file, nothing to keep running during a demo |
| Auth | JWT + bcrypt | Standard tokens; passwords are hashed one-way and never stored in plain text |
| Frontend | React 19 + Vite | Component-based UI with instant hot reload |
| Routing | react-router-dom | Multiple pages in a single-page app |

No external AI service is used. Matching is pure skill-overlap arithmetic that
runs locally, so it never fails because of a network problem.

---

## Running it

You need **Python 3.10+** and **Node.js 18+**.

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe seed.py          # optional: demo data
venv\Scripts\python.exe -m uvicorn main:app --reload
```

Runs on <http://127.0.0.1:8000>.
Interactive API docs: <http://127.0.0.1:8000/docs>

On macOS or Linux use `venv/bin/python` instead of `venv\Scripts\python.exe`.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Runs on <http://localhost:5173>.

> On Windows PowerShell, use `npm.cmd` instead of `npm` if you hit an
> execution-policy error.

### Demo accounts

After running `seed.py`, every demo account uses the password `demo123`:

| Email | Offers | Wants |
|---|---|---|
| `maria@skillswap.com` | Spanish Conversation, Salsa | React, Photography |
| `arjun@skillswap.com` | Node.js API, Python | UI/UX, Public Speaking |
| `sneha@skillswap.com` | UI/UX Design, Figma | Python, Node.js API |
| `daniel@skillswap.com` | Photography, Guitar | Spanish, Video Editing |
| `yuki@skillswap.com` | Data Analysis, Excel | Public Speaking, Guitar |
| `priya@skillswap.com` | Public Speaking, Content Writing | React, Data Analysis |
| `tom@skillswap.com` | Video Editing, Motion Graphics | Figma, Photography |

The **first account registered on a fresh database automatically becomes the
admin**, so there is always a way into the admin panel.

---

## How matching works

A swap only works when **they teach what you want** *and* **you teach what
they want** — what economists call a double coincidence of wants. The
algorithm scores that directly:

| Signal | Points |
|---|---|
| Mutual match (overlap in both directions) | +40 |
| Each skill they can teach you | +12 (max 36) |
| Each skill you can teach them | +8 (max 24) |
| Same location | +6 |
| Their rating history | up to +8 |

Skill names are compared **word by word**, not as exact strings, so `React`
still matches `React / Frontend`:

```
"React"             -> {react}
"React / Frontend"  -> {react, frontend}
overlap = {react}   -> 1/2 = 0.5  -> counts as a match
```

Anyone scoring zero is left out entirely, so the page never pads itself with
irrelevant suggestions.

---

## Project structure

```
skillswap/
├── backend/
│   ├── main.py              FastAPI app, CORS, router registration
│   ├── seed.py              demo data generator
│   ├── requirements.txt
│   └── app/
│       ├── database.py      SQLite connection and session handling
│       ├── models.py        the five database tables
│       ├── schemas.py       request/response shapes and validation
│       ├── security.py      password hashing and JWT tokens
│       ├── deps.py          "who is asking?" checks
│       └── routers/
│           ├── auth.py      signup, login, me
│           ├── users.py     profiles, browse, search
│           ├── skills.py    add, edit, delete skills
│           ├── swaps.py     the swap lifecycle
│           ├── ratings.py   feedback after a completed swap
│           ├── matches.py   the matching algorithm
│           └── admin.py     moderation, broadcasts, CSV reports
└── frontend/
    └── src/
        ├── api.js           one place that talks to the backend
        ├── auth.jsx         who is signed in, shared app-wide
        ├── index.css        the whole design system
        ├── components/
        └── pages/
```

---

## Security notes

- Passwords are hashed with bcrypt. The plain text is never stored, and
  cannot be recovered from the database.
- Login failures return the same message whether the email is unknown or the
  password is wrong, so the API cannot be used to discover which addresses
  are registered.
- Every rule is enforced on the server. Hiding a button in the UI is
  convenience, not security — the API rejects the request regardless.
- Admins can view contact details without an accepted swap, which is a
  deliberate trade-off for moderation.
- The JWT signing key falls back to a development default. Set the
  `SKILLSWAP_SECRET` environment variable before deploying anywhere real.
