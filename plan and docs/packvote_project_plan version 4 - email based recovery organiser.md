# PackVote — Project Plan

> AI-powered group travel planning. Swipe preferences, get AI recommendations, vote as a group, reach consensus.

---

## Objective

Build an end-to-end web app that eliminates the chaos of group travel planning. Each participant swipes through destination cards to express preferences, an AI pipeline aggregates those preferences and generates personalized recommendations, and the group votes via ranked-choice to reach a consensus destination.

**Target audience:** Friend groups or colleagues planning a trip together.
**Primary goal:** Working, deployable product that demonstrates LangGraph orchestration, LangSmith observability, FastAPI backend, and real-time frontend — all as a cohesive system.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend API | FastAPI | REST endpoints + WebSocket server |
| Frontend | Streamlit | Swipe UI, dashboards, voting ballot |
| AI Pipeline | LangGraph | 4-node recommendation graph |
| LLM | LangChain `ChatOpenAI` (GPT-4o) | Single model for generation + critic |
| Structured outputs | `.with_structured_output()` | Typed, validated LLM responses |
| Prompt versioning | LangSmith Hub | Version + A/B test prompts |
| Observability | LangSmith | Trace every LangGraph node |
| Database | PostgreSQL + pgvector | Relational data + vector similarity search |
| Vector embeddings | `text-embedding-3-small` (OpenAI) | Destination profile embeddings for RAG |

> **Implementation Update (2026-07-10):** The LLM and Embedding rows above are now provider-agnostic. A central factory (`core/llm.py`) reads `LLM_PROVIDER` and `EMBEDDING_PROVIDER` from `.env` and returns the appropriate LangChain model (OpenAI, Anthropic, or Google). The current deployment uses `google/gemini-1.5-pro` for LLM and `google/text-embedding-004` for embeddings.
| Organiser recovery | Resend | Email trip management link on request |
| Containerisation | Docker + Docker Compose | Local dev + deployment |
| Cloud | AWS EC2 + AWS ECR | Docker Compose on EC2 via GitHub Actions |
| CI/CD | GitHub Actions | Build, push, deploy pipeline |
| Env management | Conda (local prefix) | Python version + isolated env |
| Package management | pyproject.toml + pip | All Python dependencies |

---

## High-Level User Flow

```
Organiser creates trip
        ↓
System generates unique link per participant
        ↓
Organiser shares links (WhatsApp / any channel)
        ↓
Each participant opens their link → swipes destination cards
        ↓
Live group dashboard updates as responses arrive
        ↓
All respond (or 24hr timeout fires)
        ↓
LangGraph pipeline runs → AI recommendations generated
        ↓
Preference reveal shown to group
        ↓
Organiser opens ranked-choice vote → countdown timer starts
        ↓
All participants rank destinations
        ↓
FastAPI tallies ranked-choice result
        ↓
Winner declared → or AI tiebreak if tied
```

---

## Project Structure

Full src-layout. The `env/` folder is conda-local and gitignored. The `src/packvote/shared/` module is imported by both backend and frontend — no duplicated Pydantic schemas.

```
packvote/
├── env/                              # conda env — local to project (gitignored)
│
├── src/
│   └── packvote/
│       ├── __init__.py
│       │
│       ├── backend/
│       │   ├── __init__.py
│       │   ├── main.py               # FastAPI app, route + websocket registration
│       │   ├── routers/
│       │   │   ├── __init__.py
│       │   │   ├── trips.py          # POST /trips, /participants, /force-close, /open-vote
│       │   │   ├── responses.py      # POST /responses, GET /trips/{id}/status (polling fallback)
│       │   │   ├── votes.py          # POST /votes
│       │   │   ├── results.py        # GET /trips/{id}/result, /reveal
│       │   │   └── recovery.py       # POST /trips/recover, GET /trips/manage/{token}
│       │   ├── websockets/
│       │   │   ├── __init__.py
│       │   │   └── manager.py        # WebSocket connection manager + broadcaster
│       │   ├── pipeline/
│       │   │   ├── __init__.py
│       │   │   ├── graph.py          # LangGraph graph definition + compile
│       │   │   ├── state.py          # TripState TypedDict
│       │   │   └── nodes/
│       │   │       ├── __init__.py
│       │   │       ├── aggregate.py  # Node 1 — merge swipe responses
│       │   │       ├── retrieve.py   # Node 2 — RAG: embed query, fetch from pgvector
│       │   │       ├── recommend.py  # Node 3 — generate recs (.with_structured_output)
│       │   │       └── critic.py     # Node 4 — score + retry loop (.with_structured_output)
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   └── db.py             # SQLAlchemy ORM models (all 6 tables)
│       │   └── core/
│       │       ├── __init__.py
│       │       ├── config.py         # pydantic-settings — reads .env
│       │       ├── database.py       # engine, SessionLocal, get_db dependency
│       │       ├── email.py          # Resend client — send_management_link()
│       │       └── llm.py            # Central factory for get_llm() and get_embeddings()
│       │
│       ├── frontend/
│       │   ├── __init__.py
│       │   ├── app.py                # Streamlit entry point
│       │   ├── pages/
│       │   │   ├── __init__.py
│       │   │   ├── 1_organiser.py    # Trip creation form (now collects organiser email)
│       │   │   ├── 2_survey.py       # Swipe UI (loads via token in URL)
│       │   │   ├── 3_dashboard.py    # Live response tracker
│       │   │   ├── 4_reveal.py       # Preference reveal + AI recommendations
│       │   │   ├── 5_vote.py         # Ranked-choice ballot + countdown timer
│       │   │   ├── 6_manage.py       # Management view — all participant links, copy buttons
│       │   │   └── 7_recover.py      # "Forgot your link?" — email entry → resend management link
│       │   └── components/
│       │       ├── __init__.py
│       │       ├── swipe_card.py     # Destination card component
│       │       └── rank_widget.py    # Drag-to-rank component
│       │
│       └── shared/
│           ├── __init__.py
│           └── schemas.py            # Pydantic models shared by backend + frontend
│
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py              # LangGraph integration tests (all 4 nodes)
│   ├── test_tally.py                 # Ranked-choice algorithm unit tests
│   └── test_api.py                   # FastAPI endpoint tests (httpx)
│
├── seeds/
│   └── destinations.json             # 50-100 destination profiles — seeded into pgvector
│
├── prompts/                          # Local drafts before pushing to LangSmith Hub
│   ├── recommendation_v1.txt
│   └── critic_rubric_v1.txt
│
├── pyproject.toml                    # Package definition + all dependencies
├── environment.yml                   # Conda env spec (Python version only)
├── docker-compose.yml                # pgvector-enabled Postgres for local dev
├── Dockerfile.backend                # FastAPI container
├── Dockerfile.frontend               # Streamlit container
├── .env                              # Local secrets — gitignored
├── .env.example                      # Committed template with no real values
├── .gitignore
└── .github/
    └── workflows/
        └── deploy.yml                # Build → ECR → SSH into EC2 → docker-compose up
```

---

## Environment Setup

### Mental model

```
env/                  ← conda manages this (Python 3.11 + pip)
pyproject.toml        ← pip manages all packages from here
src/packvote/         ← editable install makes this importable everywhere
.env                  ← pydantic-settings reads this at runtime
```

Conda pins the Python version and creates an isolated environment local to the project folder. Pip (inside that conda env) installs all Python packages declared in `pyproject.toml`. The editable install (`pip install -e .`) makes `packvote` importable as a package from anywhere in the project without sys.path hacks.

---

### `environment.yml`

No `name` field — this env is identified by its path (`./env`), not a name.

```yaml
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - pip
  - pip:
      - -e ".[dev]"
```

The `-e ".[dev]"` line runs `pip install -e .[dev]` automatically after conda sets up Python — installing all project dependencies plus dev tools in one step.

---

### `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "packvote"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # Backend
    "fastapi>=0.110.0",
    "uvicorn[standard]",
    "sqlalchemy>=2.0",
    "psycopg2-binary",
    "pgvector",             # vector column type + <=> operator support
    "pydantic>=2.0",
    "pydantic-settings",
    "python-dotenv",
    "websockets",
    # Frontend
    "streamlit>=1.35.0",
    # AI pipeline
    "langchain>=0.2.0",
    "langchain-openai",     # Default provider
    "langchain-anthropic",  # Optional alternate provider
    "langchain-google-genai", # Optional alternate provider
    "langgraph>=0.1.0",
    "langsmith",
    "openai",               # direct client for embedding calls
    # Organiser recovery
    "resend",                # trip management link emails
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "httpx",        # FastAPI test client
    "ruff",         # linter
]

[tool.hatch.build.targets.wheel]
packages = ["src/packvote"]
```

---

### `src/packvote/backend/core/config.py`

Single source of truth for all environment variables. Both backend and frontend import from here.

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str

    # LLM & Embeddings Configuration
    llm_provider: str = "openai"           # "openai", "anthropic", "google"
    llm_model: str = "gpt-4o"
    embedding_provider: str = "openai"     # "openai", "google"
    embedding_model: str = "text-embedding-3-small"

    # API Keys (only the ones needed based on provider choices)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # LangSmith
    langchain_api_key: str
    langchain_project: str = "packvote"
    langchain_tracing_v2: bool = True

    # Organiser recovery
    resend_api_key: str
    resend_from_email: str = "packvote@resend.dev"

    # App
    secret_key: str
    backend_url: str = "http://localhost:8000"     # FastAPI — used for API calls
    frontend_url: str = "http://localhost:8501"     # Streamlit — used for links sent to humans (email, survey URLs)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

Import anywhere:
```python
from packvote.backend.core.config import settings
```

---

### `src/packvote/shared/schemas.py`

Pydantic models used by both backend (request/response validation) and frontend (deserialising API responses). Also used as structured output targets via `.with_structured_output()` in the LangGraph pipeline.

```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

# ── REST request models ──────────────────────────────────────────────────────

class TripCreate(BaseModel):
    name: str
    dates_rough: str
    participant_count: int
    organiser_email: str          # used only for recovery — no password, no login

class SwipeResponse(BaseModel):
    destination: str
    liked: bool

class SurveySubmit(BaseModel):
    participant_token: UUID
    swipes: list[SwipeResponse]
    budget_max: int
    unavailable_dates: list[str]

class VoteSubmit(BaseModel):
    participant_token: UUID
    ranking: list[str]   # ["Goa", "Coorg", "Kasol"]

class TripRecoverRequest(BaseModel):
    email: str

# ── REST response models ─────────────────────────────────────────────────────

class TripOut(BaseModel):
    id: UUID
    name: str
    status: str
    management_token: UUID        # returned once at creation — organiser bookmarks or emails self
    created_at: datetime

class ParticipantOut(BaseModel):
    id: UUID
    name: str
    unique_token: UUID
    survey_url: str

class RecommendationOut(BaseModel):
    destination: str
    fit_reason: str
    tradeoff: str
    budget_estimate: int

class TripManageOut(BaseModel):
    """Full management view — served only via management_token, never guessable."""
    id: UUID
    name: str
    status: str
    participants: list[ParticipantOut]   # every participant's survey_url, incl. organiser's own

# ── Structured output models (used with .with_structured_output()) ───────────

class RecommendationsOutput(BaseModel):
    """Node 3 output — LLM must return a typed list, no free-form text."""
    recommendations: list[RecommendationOut]

class CriticOutput(BaseModel):
    """Node 4 output — score drives the retry conditional edge."""
    score: float          # 0.0–1.0; retry if < 0.7
    feedback: str         # fed back into Node 3 prompt on retry

# ── Response models for reveal, result, and management endpoints ─────────

class RevealOut(BaseModel):
    """GET /trips/{id}/reveal response — aggregated preferences + AI recommendations."""
    aggregated: dict
    recommendations: list[RecommendationOut]

class ResultOut(BaseModel):
    """GET /trips/{id}/result response — final winner + vote breakdown."""
    winner: str
    vote_breakdown: dict      # {"Goa": 3, "Coorg": 1, "Kasol": 1}
    ai_summary: str           # one-line AI-generated summary of why the winner won

class OpenVoteRequest(BaseModel):
    """POST /trips/{id}/open-vote — organiser starts the voting phase."""
    management_token: UUID
    vote_duration_hours: int = 12     # default 12-hour countdown

class ForceCloseResponse(BaseModel):
    """POST /trips/{id}/force-close — organiser triggers pipeline early."""
    ok: bool
    responses_received: int
    total_participants: int
```

---

### `.env`

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/packvote

# LLM API
OPENAI_API_KEY=sk-...          # used for generation, critic, and text-embedding-3-small

# LangSmith
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=packvote
LANGCHAIN_TRACING_V2=true

# Organiser recovery
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=packvote@resend.dev

# App
SECRET_KEY=change-me-in-production
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8501
```

> **Implementation Update (2026-07-10):** The `.env` file now includes `LLM_PROVIDER`, `LLM_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `GOOGLE_API_KEY`, and `ANTHROPIC_API_KEY` variables. Only the API key for the active provider needs to be set. See `.env.example` for the full template.

---

### `.env.example`

Committed to the repo — no real values, just keys:

```env
DATABASE_URL=
OPENAI_API_KEY=
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=packvote
LANGCHAIN_TRACING_V2=true
RESEND_API_KEY=
RESEND_FROM_EMAIL=packvote@resend.dev
SECRET_KEY=
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8501
```

---

### `.gitignore`

```gitignore
# Conda local env
env/

# Secrets
.env

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/
dist/
build/

# Streamlit
.streamlit/secrets.toml

# IDE
.vscode/
.idea/
```

---

### First-time setup commands

```bash
# 1. Clone
git clone https://github.com/you/packvote
cd packvote

# 2. Create local conda env (reads environment.yml, installs Python 3.11,
#    runs pip install -e .[dev] automatically)
conda env create --prefix ./env -f environment.yml

# 3. Activate by path
conda activate ./env

# 4. Verify editable install
python -c "from packvote.backend.main import app; print('backend ok')"
python -c "from packvote.shared.schemas import TripCreate; print('shared ok')"
python -c "from packvote.frontend.app import *; print('frontend ok')"

# 5. Copy env file and fill in your keys
cp .env.example .env

# 6. Start PostgreSQL only (not the full app)
docker compose up db -d

# 7. Run backend (terminal 1)
uvicorn packvote.backend.main:app --reload

# 8. Run frontend (terminal 2)
streamlit run src/packvote/frontend/app.py
```

---

### Adding a new package mid-build

The conda env already exists — never recreate it just to add a package:

```bash
# 1. Add the package to pyproject.toml under dependencies
# 2. Then:
pip install -e ".[dev]"
```

Teammates who pull your changes run the same command — no env recreation needed.

---

### Import pattern

Because of the editable install, all imports use the full package path:

```python
# In any file anywhere in the project
from packvote.backend.core.config import settings
from packvote.backend.core.database import get_db
from packvote.shared.schemas import TripCreate, RecommendationOut
from packvote.backend.pipeline.graph import run_pipeline
```

No relative imports, no sys.path manipulation, no `../../` hacks.

---

## Database Schema

One PostgreSQL instance (pgvector image) — handles both relational data and vector similarity search. No separate vector store service.

**Docker Compose image — one line change from plain Postgres:**
```yaml
services:
  db:
    image: pgvector/pgvector:pg16   # drop-in replacement for postgres:16
```

**Enable extension on first run:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

```
trips
  id                UUID PK
  name              TEXT
  organiser_email   TEXT                    -- used only for recovery, no password
  management_token  UUID UNIQUE             -- durable, never expires — the organiser's real "identity"
  dates_rough       TEXT
  status            ENUM(setup, survey, reveal, voting, complete)
  vote_deadline     TIMESTAMP NULL          -- set when organiser opens voting; NULL until then
  created_at        TIMESTAMP

participants
  id                UUID PK
  trip_id           UUID FK → trips
  name              TEXT
  unique_token      UUID
  is_organiser      BOOLEAN DEFAULT false   -- marks the organiser's own swipe/vote row
  responded         BOOLEAN DEFAULT false
  voted             BOOLEAN DEFAULT false
  created_at        TIMESTAMP

responses
  id                UUID PK
  participant_id    UUID FK → participants
  trip_id           UUID FK → trips
  swipes            JSONB          -- [{destination: "Goa", liked: true}, ...]
  budget_max        INTEGER
  unavailable_dates JSONB          -- ["2025-08-22", "2025-08-23"]
  created_at        TIMESTAMP

recommendations
  id                UUID PK
  trip_id           UUID FK → trips
  destination       TEXT
  fit_reason        TEXT
  tradeoff          TEXT
  budget_estimate   INTEGER
  rank              INTEGER
  prompt_version    TEXT           -- "v1", "v2" — for A/B tracking in LangSmith
  model_used        TEXT           -- "gpt-4o" (or whichever model is configured via LLM_PROVIDER/LLM_MODEL)
  created_at        TIMESTAMP

votes
  id                UUID PK
  participant_id    UUID FK → participants
  trip_id           UUID FK → trips
  ranking           JSONB          -- ["Goa", "Coorg", "Kasol"]
  created_at        TIMESTAMP

destinations                        -- RAG knowledge base, seeded once from seeds/destinations.json
  id                UUID PK
  name              TEXT
  vibe_tags         TEXT[]
  budget_low        INTEGER
  budget_high       INTEGER
  best_months       TEXT[]
  activities        TEXT[]
  embedding         vector(1536)   -- text-embedding-3-small output, queried with <=> cosine distance

> **Implementation Update (2026-07-10):** The embedding dimension is tied to the provider. `text-embedding-3-small` uses 1536, but Google's `text-embedding-004` uses 768. The SQLAlchemy model and database schema must be updated if swapping providers mid-project.
```

**RAG query pattern — same SQLAlchemy session, no new service:**
```python
results = db.execute(
    text("""
        SELECT name, vibe_tags, budget_low, budget_high, best_months
        FROM destinations
        ORDER BY embedding <=> :query_embedding
        LIMIT 5
    """),
    {"query_embedding": query_embedding}
).fetchall()
```

**Design note — no `organisers` table.** `organiser_email` and `management_token` live directly on `trips`. No login, no session, no password. The `management_token` is the organiser's real identity for a given trip — durable, never expires, and re-sendable to their email on request. This is deliberately lighter than an OAuth-based `organisers` table: one trip, one durable token, one recovery path. If a person organises multiple trips, each trip gets its own independent `management_token` — there's no cross-trip account to log into, which matches the zero-friction philosophy of the rest of the app.

---

## Phase-by-Phase Breakdown

### Phase 1 — Setup

**What happens:** Organiser creates a trip and the system generates participant links — including one for the organiser's own survey responses, plus a durable management link.

**User experience:**
- Organiser fills: trip name, rough dates, participant names, and their own email (recovery only — no password, no login)
- System generates:
  - One UUID-based `unique_token` per participant, **including a `participants` row for the organiser themself** (flagged `is_organiser=true`) so they can swipe and vote like everyone else
  - One `management_token` for the trip — a durable link the organiser bookmarks or receives by email
- Organiser copies participant links and shares via WhatsApp or any existing channel — no SMS/email integration for participants
- If the organiser loses their management link later, they visit `/recover`, enter their email, and get it re-sent via Resend

**Stack:**
- `POST /trips` — creates trip record with `organiser_email` + generated `management_token`, also creates the organiser's own `participants` row
- `POST /trips/{trip_id}/participants` — registers remaining participants, generates UUID tokens
- `GET /trips/manage/{management_token}` — management view: trip status + every participant's `survey_url` with a copy button (this is what actually fixes "I lost the participant link")
- `POST /trips/recover` — takes an email, looks up all trips for it, emails each `management_token` link via Resend
- PostgreSQL stores `trips` and `participants`

**Important — all human-facing links use `frontend_url`, never `backend_url`.** `survey_url` and the management link both point at the Streamlit app (`:8501`), not the FastAPI backend (`:8000`). `ParticipantOut.survey_url` is built at serialization time, e.g.:

```python
# routers/trips.py — building ParticipantOut from a Participant row
def to_participant_out(participant: Participant) -> ParticipantOut:
    return ParticipantOut(
        id=participant.id,
        name=participant.name,
        unique_token=participant.unique_token,
        survey_url=f"{settings.frontend_url}/survey?token={participant.unique_token}",
    )
```

Matches how `2_survey.py` reads `?token=` from `st.query_params` — same query-param pattern the management link uses.

**Recovery endpoint:**
```python
# routers/recovery.py
from packvote.backend.core.email import send_management_link

@router.post("/trips/recover")
def recover_trip(payload: TripRecoverRequest, db: Session = Depends(get_db)):
    trips = db.query(Trip).filter_by(organiser_email=payload.email).all()
    for trip in trips:
        send_management_link(payload.email, trip.name, trip.management_token)
    # Always return success — don't reveal whether the email had trips or not
    return {"sent": True}

@router.get("/trips/manage/{management_token}")
def manage_trip(management_token: UUID, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter_by(management_token=management_token).first()
    if not trip:
        raise HTTPException(404)
    return trip   # serialises to TripManageOut — every participant's survey_url, incl. organiser's own
```

**Email util — `core/email.py`:**
```python
import resend
from packvote.backend.core.config import settings

resend.api_key = settings.resend_api_key

def send_management_link(to_email: str, trip_name: str, management_token: str):
    resend.Emails.send({
        "from": settings.resend_from_email,
        "to": to_email,
        "subject": f"Your PackVote trip: {trip_name}",
        # frontend_url, not backend_url — 6_manage.py is a Streamlit page, reads ?token= not a path segment
        "html": f"<p>Manage your trip here: {settings.frontend_url}/manage?token={management_token}</p>",
    })
```

**Frontend:**
- `1_organiser.py` — trip creation form now includes an email field; on success, shows the management link directly on screen (organiser can bookmark immediately, no need to even check email)
- `6_manage.py` — reads `?token=` from URL, calls `GET /trips/manage/{token}`, renders every participant's link with a **copy** button
- `7_recover.py` — single email input, calls `POST /trips/recover`, shows a generic "if that email has trips, we've sent the link" message

---

### Phase 2 — Swipe Survey

**What happens:** Each participant opens their unique link and swipes through destination cards.

**User experience:**
- 8–10 destination cards shown one at a time (Goa, Manali, Coorg, Kasol, Pondicherry…)
- Each card shows: destination name, vibe tags, rough budget range
- Swipe right (interested) or left (not interested) via button
- After cards: max budget slider (₹5k–₹30k) + unavailable date picker
- Submit — done in under 2 minutes, no login required

**Stack:**
- Streamlit page `2_survey.py` reads `?token=` from URL query params
- Token validated via `GET /participants/validate/{token}` on page load
- `POST /responses` — saves swipe JSONB + budget + date constraints
- Participant marked `responded = true` in DB

**Status guard (Gap fix):** `POST /responses` first checks `trips.status == "survey"`. If the trip is in any other status, it returns 409 Conflict. This prevents responses from being submitted after the pipeline has already run.

**Trigger logic — after saving response:**
```python
# Status guard — reject if trip is not in survey phase
trip = db.query(Trip).filter_by(id=trip_id).first()
if trip.status != "survey":
    raise HTTPException(409, "Survey is no longer accepting responses")

responded_count = db.query(func.count(Participant.id)).filter(
    Participant.trip_id == trip_id,
    Participant.responded == True
).scalar()
total = db.query(func.count(Participant.id)).filter(
    Participant.trip_id == trip_id
).scalar()

if responded_count == total:
    background_tasks.add_task(run_langgraph_pipeline, trip_id)
```

**Force-close endpoint (Gap fix) — `routers/trips.py`:**

If one or more participants never respond, the organiser can force-close the survey and trigger the pipeline with whatever responses have been collected. Requires the `management_token` for authorization.

```python
@router.post("/trips/{trip_id}/force-close")
def force_close_survey(trip_id: UUID, management_token: UUID, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter_by(id=trip_id, management_token=management_token).first()
    if not trip:
        raise HTTPException(404)
    if trip.status != "survey":
        raise HTTPException(409, "Trip is not in survey phase")

    responded = db.query(func.count(Participant.id)).filter(
        Participant.trip_id == trip_id,
        Participant.responded == True
    ).scalar()
    total = db.query(func.count(Participant.id)).filter(
        Participant.trip_id == trip_id
    ).scalar()

    if responded == 0:
        raise HTTPException(400, "Cannot close survey — no responses received yet")

    # Trigger pipeline with partial responses
    trip.status = "reveal"
    db.commit()
    background_tasks.add_task(run_langgraph_pipeline, trip_id)

    return ForceCloseResponse(ok=True, responses_received=responded, total_participants=total)
```

**Note on destination cards:** Seed a static JSON list of 20–30 destinations with vibe tags and budget ranges. Show a randomised subset of 10 per participant. Future extension: swap static seed for a real-time pricing agent.

---

### Phase 3 — Live Group Dashboard

**What happens:** Everyone can see who has responded in real time.

**User experience:**
- Shared dashboard URL — organiser drops this in the group chat alongside survey links
- Each participant shown with a live status: green checkmark (responded) or amber clock (pending)
- Counter: "3 of 5 responded"
- Page stays in waiting state until all respond — builds anticipation

**Stack:**
- FastAPI WebSocket: `WS /ws/trips/{trip_id}/status`
- On each `POST /responses`, backend broadcasts updated participant status to all connected clients
- Streamlit `3_dashboard.py` connects via WebSocket, re-renders on each broadcast
- When all respond → `BackgroundTasks` triggers LangGraph pipeline

**Polling fallback (Gap fix):** Mobile browsers and backgrounding kill WebSocket connections. Add a REST fallback:

```python
@router.get("/trips/{trip_id}/status")
def get_trip_status(trip_id: UUID, db: Session = Depends(get_db)):
    """Polling fallback for when WebSocket connection drops."""
    responded = db.query(func.count(Participant.id)).filter(
        Participant.trip_id == trip_id,
        Participant.responded == True
    ).scalar()
    total = db.query(func.count(Participant.id)).filter(
        Participant.trip_id == trip_id
    ).scalar()
    trip = db.query(Trip).filter_by(id=trip_id).first()
    return {"responded_count": responded, "total": total, "status": trip.status}
```

The Streamlit frontend wraps the WebSocket connection in a try/except. If the connection drops, it falls back to polling `GET /trips/{id}/status` every 5 seconds.

---

### Phase 4 — AI Pipeline (LangGraph)

**What happens:** The core AI engineering piece. 4-node LangGraph graph runs, producing recommendations.

**Graph state — `src/packvote/backend/pipeline/state.py`:**
```python
from typing import TypedDict

class TripState(TypedDict):
    trip_id: str
    prompt_version: str                  # "v1" or "v2" — set by A/B coin flip before pipeline runs
    responses: list[dict]
    aggregated: dict
    retrieved_destinations: list[dict]   # populated by Node 2 RAG retrieval
    recommendations: list[dict]
    critic_score: float
    critic_feedback: str
    retry_count: int
```

**DB session in LangGraph nodes.** LangGraph nodes are plain functions — they don't run inside FastAPI route handlers, so `Depends(get_db)` is unavailable. Each node that needs database access (Node 1 and Node 2) creates its own session using `with SessionLocal() as db:` and closes it when done. This keeps each node self-contained and avoids passing a long-lived session through the graph state.

---

#### Node 1 — Aggregate (`aggregate.py`)

Pulls all swipe responses from PostgreSQL and computes group-level signals.

```python
from statistics import median
from collections import Counter
from packvote.backend.core.database import SessionLocal
from packvote.backend.models.db import Response, Destination

def aggregate_node(state: TripState) -> TripState:
    with SessionLocal() as db:
        # 1. Pull all responses for this trip
        responses = db.query(Response).filter_by(trip_id=state["trip_id"]).all()
        state["responses"] = [
            {"swipes": r.swipes, "budget_max": r.budget_max, "unavailable_dates": r.unavailable_dates}
            for r in responses
        ]

        # 2. Count swipe-rights per destination
        dest_counts = Counter()
        liked_names = []
        for r in responses:
            for swipe in r.swipes:
                if swipe["liked"]:
                    dest_counts[swipe["destination"]] += 1
                    liked_names.append(swipe["destination"])
        top_destinations = [name for name, _ in dest_counts.most_common(5)]

        # 3. Compute median budget across all participants
        budgets = [r.budget_max for r in responses]
        budget_sweet_spot = int(median(budgets)) if budgets else 15000

        # 4. JOIN destinations table to look up vibe_tags for liked destinations
        #    (responses only store destination names, NOT vibe tags)
        dest_rows = db.query(Destination).filter(Destination.name.in_(set(liked_names))).all()
        all_vibes = []
        for d in dest_rows:
            all_vibes.extend(d.vibe_tags or [])
        vibe_overlap = [tag for tag, _ in Counter(all_vibes).most_common(3)]

        # 5. Union all unavailable dates
        all_conflicts = set()
        for r in responses:
            all_conflicts.update(r.unavailable_dates or [])

    state["aggregated"] = {
        "top_destinations": top_destinations,
        "budget_sweet_spot": budget_sweet_spot,
        "vibe_overlap": vibe_overlap,
        "date_conflicts": sorted(all_conflicts),
    }
    return state
```

**Single LLM instance — used by Node 3 and Node 4:**
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")
```

> **Implementation Update (2026-07-10):** The hardcoded pattern above is replaced in practice by `get_llm()` from the central factory below. Nodes import `from packvote.backend.core.llm import get_llm` and call `llm = get_llm()` instead.

**Central LLM Factory — `src/packvote/backend/core/llm.py`:**
```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from packvote.backend.core.config import settings

def get_llm():
    if settings.llm_provider == "openai":
        return ChatOpenAI(model=settings.llm_model)
    elif settings.llm_provider == "anthropic":
        return ChatAnthropic(model=settings.llm_model)
    elif settings.llm_provider == "google":
        return ChatGoogleGenerativeAI(model=settings.llm_model)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

def get_embeddings():
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddings(model=settings.embedding_model)
    elif settings.embedding_provider == "google":
        return GoogleGenerativeAIEmbeddings(model=settings.embedding_model)
    raise ValueError(f"Unknown Embedding provider: {settings.embedding_provider}")
```

One factory, defined once, imported wherever a pipeline node needs it. This makes swapping models as easy as changing a `.env` variable.

---

#### Node 2 — RAG Retrieval (`retrieve.py`)

Converts aggregated group preferences into a query string, embeds it, and retrieves the top-5 most relevant destination profiles from the pgvector table. These grounded profiles become context for Node 3.

```python
from sqlalchemy import text
from packvote.backend.core.database import SessionLocal
from packvote.backend.core.llm import get_embeddings

def retrieve_node(state: TripState) -> TripState:
    agg = state["aggregated"]

    # Build a natural language query from aggregated signals
    query = (
        f"{' '.join(agg['vibe_overlap'])} destination "
        f"budget {agg['budget_sweet_spot']} INR "
        f"avoid {' '.join(agg.get('date_conflicts', []))}"
    )

    # Standardized LangChain Embeddings interface
    embeddings = get_embeddings()
    query_embedding = embeddings.embed_query(query)

    # Cosine similarity search via pgvector — own DB session (not FastAPI Depends)
    with SessionLocal() as db:
        results = db.execute(
            text("""
                SELECT name, vibe_tags, budget_low, budget_high, best_months, activities
                FROM destinations
                ORDER BY embedding <=> :emb
                LIMIT 5
            """),
            {"emb": query_embedding}
        ).fetchall()

    state["retrieved_destinations"] = [dict(r._mapping) for r in results]
    return state
```

**Why pgvector over a standalone vector store:** The destinations table lives in the same Postgres instance as trips, participants, and responses. One DB connection, one Docker service, one backup strategy. For 50-100 destination profiles, pgvector's performance is more than sufficient.

---

#### Node 3 — Generate Recommendations (`recommend.py`)

Calls the LLM with a versioned prompt and grounded destination context from Node 2. Uses `.with_structured_output()` — response is a typed `RecommendationsOutput`, no JSON parsing, no try/except.

```python
from langchain import hub
from packvote.shared.schemas import RecommendationsOutput
from packvote.backend.core.llm import get_llm

def recommend_node(state: TripState) -> TripState:
    llm = get_llm()
    # Pull the prompt version assigned by the A/B coin flip (stored in state)
    version = state["prompt_version"]
    prompt = hub.pull(f"packvote/recommendation-prompt:{version}")

    # Structured output — LLM must conform to RecommendationsOutput schema
    structured_llm = llm.with_structured_output(RecommendationsOutput)
    chain = prompt | structured_llm

    result: RecommendationsOutput = chain.invoke({
        **state["aggregated"],
        "retrieved_destinations": state["retrieved_destinations"],   # grounded context
        "critic_feedback": state.get("critic_feedback", ""),
    })

    state["recommendations"] = [r.model_dump() for r in result.recommendations]
    return state
```

**Prompt template — `prompts/recommendation_v1.txt` (push this to LangSmith Hub):**

```
You are a group travel advisor. Given the following group preferences and
available destination profiles, recommend exactly 3 destinations.

Group preferences:
- Top swiped destinations: {top_destinations}
- Budget sweet spot: {budget_sweet_spot} INR
- Shared vibes: {vibe_overlap}
- Unavailable dates: {date_conflicts}

Available destination profiles (recommend only from these):
{retrieved_destinations}

{critic_feedback}

For each recommendation provide:
1. Destination name (must be from the profiles above)
2. Why it fits this specific group (cite preference overlaps)
3. Which preference it compromises on and why it is still worth it
4. Estimated budget per person in INR (use the profile's budget range)
```

---

#### Node 4 — Self-Critic (`critic.py`)

Scores the recommendations against the group data. Uses `.with_structured_output()` — `result.score` is a direct float, no parsing needed. If quality is below threshold, loops back to Node 3 with feedback. Max 2 retries.

```python
from langchain import hub
from packvote.shared.schemas import CriticOutput
from packvote.backend.core.llm import get_llm

def critic_node(state: TripState) -> TripState:
    llm = get_llm()
    critic_prompt = hub.pull("packvote/critic-rubric:v1")

    # Structured output — result.score and result.feedback are typed directly
    structured_llm = llm.with_structured_output(CriticOutput)
    chain = critic_prompt | structured_llm

    result: CriticOutput = chain.invoke({
        "recommendations": state["recommendations"],
        "aggregated": state["aggregated"],
    })

    state["critic_score"] = result.score
    state["critic_feedback"] = result.feedback
    return state

def should_retry(state: TripState) -> str:
    if state["critic_score"] < 0.7 and state["retry_count"] < 2:
        state["retry_count"] += 1
        return "retry"
    # Gap fix: log a warning if we're accepting subpar recommendations due to retry cap
    if state["critic_score"] < 0.7:
        import logging
        logging.warning(
            f"Trip {state['trip_id']}: accepting recommendations with score "
            f"{state['critic_score']:.2f} after {state['retry_count']} retries (cap reached)"
        )
    return "output"
```

**Critic rubric — `prompts/critic_rubric_v1.txt`:**

```
Score these travel recommendations from 0.0 to 1.0.

Deduct points if:
- Any recommendation does not cite specific group preference data
- Budget estimate falls outside the group sweet spot by more than 20%
- No compromise pick is included
- Unavailable dates are not respected
- Any recommended destination is not from the retrieved profiles list

Provide a score and specific actionable feedback for improvement.
```

---

#### Graph wiring — `graph.py`

```python
from langgraph.graph import StateGraph, END
from packvote.backend.pipeline.state import TripState
from packvote.backend.pipeline.nodes.aggregate import aggregate_node
from packvote.backend.pipeline.nodes.retrieve import retrieve_node
from packvote.backend.pipeline.nodes.recommend import recommend_node
from packvote.backend.pipeline.nodes.critic import critic_node, should_retry

def build_graph() -> StateGraph:
    graph = StateGraph(TripState)

    graph.add_node("aggregate", aggregate_node)
    graph.add_node("retrieve", retrieve_node)       # Node 2 — RAG
    graph.add_node("recommend", recommend_node)
    graph.add_node("critic", critic_node)

    graph.set_entry_point("aggregate")
    graph.add_edge("aggregate", "retrieve")         # aggregate → RAG → recommend
    graph.add_edge("retrieve", "recommend")
    graph.add_edge("recommend", "critic")
    graph.add_conditional_edges(
        "critic",
        should_retry,
        {"retry": "recommend", "output": END},     # retry skips retrieve (context already in state)
    )

    return graph.compile()

pipeline = build_graph()
```

---

#### Prompt versioning + A/B testing

Both prompts are versioned independently in LangSmith Hub:
- `packvote/recommendation-prompt` → versions v1, v2, v3…
- `packvote/critic-rubric` → versions v1, v2…

To run an A/B test between prompt versions:

```python
import random

version = "v1" if random.random() < 0.5 else "v2"
prompt = hub.pull(f"packvote/recommendation-prompt:{version}")
```

LangSmith groups all runs by prompt version automatically. Compare which version's recommendations correlated with higher first-choice vote wins in the comparison view.

Changing a prompt never requires a code deploy — push a new version to the hub and it is live on the next pipeline run.

---

### Phase 5 — Preference Reveal

**What happens:** Before showing recommendations, show the group what they collectively wanted.

**User experience:**
- "Your group swiped right on beach destinations 14 times"
- Budget distribution bar chart (one bar per participant)
- Top 3 shared vibe tags highlighted
- Date conflict calendar — which dates are blocked
- AI recommendations appear below with reasoning per destination

**Stack:**
- `GET /trips/{trip_id}/reveal` — returns aggregated dict + recommendations list. **Status guard:** requires `trips.status IN ("reveal", "voting", "complete")`.
- Streamlit `4_reveal.py` renders `st.bar_chart()` for budget, card components for recs
- WebSocket notifies all connected clients when pipeline finishes and reveal is ready

**Open-vote endpoint (Gap fix) — `routers/trips.py`:**

After the reveal, the organiser must explicitly open the voting phase. This transitions `trips.status` from `reveal` → `voting` and sets the `vote_deadline`.

```python
from datetime import datetime, timedelta

@router.post("/trips/{trip_id}/open-vote")
def open_vote(trip_id: UUID, payload: OpenVoteRequest, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter_by(id=trip_id, management_token=payload.management_token).first()
    if not trip:
        raise HTTPException(404)
    if trip.status != "reveal":
        raise HTTPException(409, "Trip is not in reveal phase — cannot open voting yet")

    trip.status = "voting"
    trip.vote_deadline = datetime.utcnow() + timedelta(hours=payload.vote_duration_hours)
    db.commit()
    return {"status": "voting", "vote_deadline": trip.vote_deadline.isoformat()}
```

---

### Phase 6 — Live Vote

**What happens:** Ranked-choice ballot with countdown timer and blurred live leaderboard.

**User experience:**
- 3 destination cards, draggable to rank (1st, 2nd, 3rd)
- Countdown timer (organiser sets duration — default 12 hours)
- Blurred leaderboard updates as votes arrive — shows vote count but not rankings
- Timer hits zero → leaderboard unblurs → winner shown

**Stack:**
- `POST /votes` — saves ranked ballot JSONB. **Status guard:** requires `trips.status == "voting"`, returns 409 otherwise.
- FastAPI WebSocket: `WS /ws/trips/{trip_id}/vote-status` — broadcasts vote count to all clients
- `GET /trips/{trip_id}/result` — triggers tally at timer expiry or when all have voted. **Status guard:** requires `trips.status IN ("voting", "complete")`.

**Ranked-choice tally — `src/packvote/backend/routers/results.py`:**

```python
def ranked_choice_tally(ballots: list[list[str]]) -> str:
    candidates = set(c for ballot in ballots for c in ballot)
    while True:
        counts = {c: 0 for c in candidates}
        for ballot in ballots:
            for choice in ballot:
                if choice in candidates:
                    counts[choice] += 1
                    break
        total = sum(counts.values())
        for candidate, count in counts.items():
            if count > total / 2:
                return candidate                          # majority winner
        # eliminate last place, redistribute
        last = min(counts, key=counts.get)
        candidates.remove(last)
        if len(candidates) == 1:
            return candidates.pop()
```

**Tiebreak (Gap fix):** If still tied after full IRV elimination (rare with 3 candidates), the winner is the tied destination with the **lowest `budget_estimate`** from the recommendations table. This is deterministic, testable, and avoids an extra LLM call. If budgets are also equal, the destination that was swiped-right by more participants wins.

---

### Phase 7 — Result

**What happens:** Winner declared, group notified.

**User experience:**
- Full-screen winner reveal: destination name, vote breakdown, one-line AI summary of why this won
- "Share result" button → generates a text summary card to drop back into WhatsApp

**Stack:**
- `GET /trips/{trip_id}/result` — returns winner, vote breakdown, AI summary
- AI summary is a single `chain.invoke()` call, not a full LangGraph pipeline

---

## WebSocket Channels

Two independent WebSocket channels served by `websockets/manager.py`. Each channel broadcasts to its own set of connected clients.

| Channel | Endpoint | Triggered by | Payload | Consumer |
|---|---|---|---|---|
| Response status | `WS /ws/trips/{id}/status` | `POST /responses` | `{participant_id, responded_count, total}` | `3_dashboard.py` — live response tracker |
| Vote status | `WS /ws/trips/{id}/vote-status` | `POST /votes` | `{voted_count, total}` (no rankings) | `5_vote.py` — blurred leaderboard counter |

The vote channel intentionally omits rankings in its payload — the leaderboard stays blurred until timer expiry, at which point the frontend calls `GET /trips/{id}/result` to fetch the final tally.

---

## LangSmith Observability — What Gets Tracked

Every LangGraph run produces a trace automatically. No manual instrumentation needed beyond setting `LANGCHAIN_TRACING_V2=true`.

| What | Where in LangSmith |
|---|---|
| Each node's input + output | Run detail → spans |
| Token count per node | Metadata |
| Latency per node (incl. RAG embed call) | Timeline view |
| Which LLM was used | Model tag |
| Which prompt version was used | Prompt tag |
| Critic score + retry count | Custom metadata |
| Retrieved destinations (RAG context) | Node 2 output span |
| Full trip ID for correlation | Run name |

Use LangSmith's comparison view to evaluate prompt v1 vs v2 — filter by `prompt_version` tag and compare critic scores against eventual vote outcomes.

---

## AI Assistant Workflow Rules

To maintain consistency across different chat sessions, the AI assistant must follow these rules during development:
1. **Never delete original plan text:** If we deviate from the technical design (e.g., adding a new DB column or API route), add a blockquote like `> **Implementation Update (Date):** [Reason for change]` next to the relevant section instead of deleting or overwriting the original text.
2. **Update the Build Order Checklist:** When a step in the Build Order is completed, mark its checkbox (`- [x]`) to track progress visually.
3. **Use Artifacts for Micro-tasks:** Do not clutter this document with granular to-dos. Use the AI's internal `task.md` artifact to track messy micro-tasks during execution, and close it when the step is complete.

---

## Build Order

Build in this sequence. Each step is independently testable before wiring the next.

**Git Flow Workflow:**
To demonstrate professional software engineering practices, we will use Git feature branching during execution.
1. `main` will remain stable.
2. For each step below, we will branch out (e.g., `git checkout -b feat/step-0-scaffold`).
3. We will execute the step, commit the code, and merge back to `main` before proceeding to the next step.

- [x] **Step 0 — Scaffold**
- Create folder structure, `pyproject.toml`, `environment.yml`
- Run `conda env create --prefix ./env -f environment.yml`
- Verify editable install: `python -c "from packvote.shared.schemas import TripCreate"`
- Commit skeleton with all `__init__.py` files in place

- [x] **Step 1 — Backend foundation**
- `core/database.py` — SQLAlchemy engine, `SessionLocal`, `get_db` dependency
- `core/config.py` — pydantic-settings reading `.env`
- `models/db.py` — ORM models for all 6 tables (including destinations), `trips` includes `organiser_email` + `management_token` + `vote_deadline`
- `routers/trips.py` — `POST /trips` (creates trip + organiser's own `participants` row), `POST /trips/{id}/participants`
- Docker Compose with pgvector Postgres (`docker compose up db -d`)
- Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
- Seed destinations: embed `seeds/destinations.json` → insert into `destinations` table
- Test: `pytest tests/test_api.py::test_create_trip`

- [x] **Step 2 — Survey data layer**
- `routers/responses.py` — `POST /responses` with token validation + **status guard** (reject if trip not in `survey` phase)
- Pipeline trigger logic in background task (with A/B `prompt_version` coin flip)
- `GET /trips/{id}/status` — polling fallback endpoint for dashboard
- `POST /trips/{id}/force-close` — organiser triggers pipeline early with partial responses
- Test: submit mock swipes, verify `responded = true` in DB
- Test: verify status guard rejects responses when trip is not in survey phase

- [x] **Step 3 — Streamlit survey UI**
- `frontend/pages/2_survey.py` — card swipe with `st.button` (upgrade to drag later)
- Budget slider + date picker
- Reads `?token=` from `st.query_params`
- Connects to `POST /responses`

- [ ] **Step 3.5 — Organiser recovery**
- `core/email.py` — Resend client wrapper, `send_management_link()`
- `routers/recovery.py` — `GET /trips/manage/{token}`, `POST /trips/recover`
- `frontend/pages/6_manage.py` — management view with copy-link buttons per participant
- `frontend/pages/7_recover.py` — email entry, calls `/trips/recover`
- Test: create trip, hit recover endpoint, verify email send is called with correct token (mock Resend in tests)

- [ ] **Step 4 — LangGraph pipeline**
- Build and unit-test all 4 nodes in isolation with mocked state
- Start with Node 1 (aggregate) — JOINs `destinations` table for `vibe_tags` via own `SessionLocal()`
- Add Node 2 (retrieve): pgvector query via own `SessionLocal()`, verify correct destinations for test query
- Add Node 3 + Node 4 with `.with_structured_output()` — verify typed responses
- Node 3 reads `state["prompt_version"]` to dynamically pull prompt from LangSmith Hub
- Node 4 `should_retry()` — hard cap at 2 retries, logs warning when cap reached
- Wire graph in `graph.py`
- Connect LangSmith (`LANGCHAIN_TRACING_V2=true`) and verify all 4 nodes appear as spans

- [ ] **Step 5 — Prompt versioning**
- Push prompt text files to LangSmith Hub
- Replace hardcoded strings with `hub.pull()`
- Verify prompt version tag appears on runs in LangSmith

- [ ] **Step 6 — WebSocket live dashboard**
- `websockets/manager.py` — connection manager + broadcast helper (supports multiple channels)
- Wire status broadcast into `POST /responses` handler
- `frontend/pages/3_dashboard.py` — live status UI

- [ ] **Step 7 — Reveal + voting**
- `routers/results.py` — `/reveal` (status guard: requires `reveal`/`voting`/`complete`) and `/result` endpoints
- `POST /trips/{id}/open-vote` — transitions `reveal` → `voting`, sets `vote_deadline`
- `frontend/pages/4_reveal.py` — charts + AI rec cards
- `routers/votes.py` + `frontend/pages/5_vote.py` — ballot + countdown (status guard: requires `voting`)
- Wire vote-status broadcast into `POST /votes` handler
- Ranked-choice tally with `pytest tests/test_tally.py`
- Deterministic tiebreak: lowest `budget_estimate` wins (no extra LLM call)

- [ ] **Step 8 — Result + polish**
- Winner reveal screen + share card
- End-to-end test with 3 simulated participants via `httpx`
- Verify all status transitions: `setup → survey → reveal → voting → complete`

- [ ] **Step 9 — Deployment**
- `Dockerfile.backend` + `Dockerfile.frontend`
- `docker-compose.yml` wiring all three services (pgvector image for DB)
- GitHub Actions `deploy.yml` — build → ECR → SSH into EC2 → pull & restart
- Environment variables via AWS Secrets Manager (incl. `RESEND_API_KEY`)

---

## Key Engineering Decisions

**Local conda env via `--prefix ./env`.** The env lives inside the project folder like a `.venv` — visible, local, gitignored. Activated by path (`conda activate ./env`). Recreated on any machine from `environment.yml`.

**`environment.yml` pins Python only. `pyproject.toml` pins packages.** Clean separation of concerns. Adding a dependency mid-build is just `pip install -e ".[dev]"` — no env recreation.

**src-layout with editable install.** `src/packvote` is installed as a package via `pip install -e .`. All imports use full package paths. No relative imports, no sys.path hacks, works from any directory in the project.

**Shared Pydantic schemas.** `packvote.shared.schemas` is imported by both backend and frontend, and also used as `.with_structured_output()` targets in the pipeline. Define once, no duplication.

**PGVector over a standalone vector store.** The destinations knowledge base lives in the same Postgres instance as all relational data. One connection string, one Docker service, one backup strategy. For 50-100 destination profiles, pgvector is more than sufficient — adding a dedicated vector DB would be infrastructure overhead with no benefit.

**`.with_structured_output()` for Node 3 and Node 4.** Both LLM calls in the pipeline return typed Pydantic models — no JSON parsing, no try/except, no stripping markdown fences. `result.score` is a float, `result.recommendations` is a typed list. This is the correct pattern whenever LLM output feeds directly into application logic.

**Two WebSocket channels, same manager.** Response-status and vote-status are separate channels with separate client sets. The vote channel intentionally omits rankings — it only broadcasts a count, keeping the leaderboard blurred until timer expiry.

**`frontend_url` separate from `backend_url`.** FastAPI (`:8000`) and Streamlit (`:8501`) run on different hosts/ports. Any link sent to a human — `survey_url`, the management link in recovery emails — must point at `frontend_url`. Links used for API calls (`BACKEND_URL` in Streamlit's own requests) point at `backend_url`. Mixing these up is a real bug class, not a style choice — an email linking to `backend_url/manage/...` would hit FastAPI directly and 404, since `/manage` only exists as a Streamlit page.

**No SMS/email for participants, lightweight email for organiser recovery.** Participants still get links shared manually (WhatsApp) — no Twilio. The organiser is the one exception: a `management_token` on the trip plus a one-field email recovery flow via Resend solves link loss without building a full account system. This was a deliberate scope decision after identifying that the organiser had no durable identity in the original design — losing their tab meant losing the trip permanently, with no recovery path at all.

**UUID tokens for auth, `management_token` for organiser identity.** Participants remain fully anonymous — the token in their URL is their identity, no accounts. The organiser gets one additional durable token (not tied to login/session) that can be re-sent by email on request. Still no auth middleware, no password, no OAuth — just a second, longer-lived token type.

**Streamlit for frontend.** Faster to ship than React. Acceptable for a portfolio project — mention in interviews that you'd replace with Next.js for production.

**Single LLM — OpenAI only.** `ChatOpenAI` (GPT-4o) handles both generation (Node 3) and critic scoring (Node 4). Chosen for budget reasons — one API key, one billing surface. LangChain's model interface still means swapping in a second provider later is a one-node addition, not a rewrite.

> **Implementation Update (2026-07-10):** The project is now fully model-agnostic via `core/llm.py`. The active provider is configured through `LLM_PROVIDER` and `EMBEDDING_PROVIDER` in `.env`. Current deployment uses Google Gemini.

**JSONB for swipes and votes.** Schema flexibility without complex relational joins. Aggregation in Python not SQL.

**FastAPI `BackgroundTasks` for pipeline trigger.** `POST /responses` returns 200 immediately. Pipeline runs async in background — no blocking, no timeout risk.

**Retry skips RAG node.** On critic retry, the graph loops back to Node 3 (recommend) not Node 2 (retrieve). Retrieved destinations are already in state — no need to re-embed and re-query on every retry.

---

## Placement Interview Talking Points

- **Python packaging:** "I used a src-layout with `pyproject.toml` and an editable install. The package is importable from anywhere in the project without sys.path manipulation. Conda manages the Python version locally via a prefix-based env inside the project folder."

- **LangGraph:** "I modelled the recommendation pipeline as a stateful graph with 4 nodes — aggregate, RAG retrieval, generate, and critic. The critic node creates a conditional retry edge: if recommendations score below 0.7, it feeds back specific critique to the generation node and retries up to 2 times. The retry skips the RAG node since retrieved context is already in state."

- **RAG + pgvector:** "Instead of a standalone vector store, I used pgvector — a Postgres extension that adds a vector column type and cosine similarity search. The destination knowledge base lives in the same DB instance as all relational data, so I have one connection, one Docker service, and one backup strategy. The retrieval node embeds the aggregated group preferences with `text-embedding-3-small` and fetches the top-5 relevant destinations. This grounds the LLM — it recommends only from retrieved profiles, which prevents hallucinated budget estimates."

> **Implementation Update (2026-07-10):** Update talking point for model-agnostic approach: "...embeds the aggregated preferences via our `get_embeddings()` factory (currently using Google's `text-embedding-004`)."

- **Structured outputs:** "Wherever the LLM output feeds directly into application logic — Node 3 and Node 4 — I used `.with_structured_output()` with Pydantic models. `result.score` is a float I can compare directly, `result.recommendations` is a typed list I can iterate. No JSON parsing, no try/except, no stripping markdown fences. The same Pydantic models in `shared/schemas.py` are reused as FastAPI response models — defined once."

- **LangSmith:** "Every pipeline run is traced automatically. I can see token cost, latency, and which prompt version was used for each run. I used this to A/B test prompt versions and picked the one that correlated with higher first-choice vote wins."

- **Prompt versioning:** "Prompts are versioned in LangSmith Hub and pulled at runtime with `hub.pull()`. Changing a prompt never requires a code deploy — push a new version and it is live on the next pipeline run."

- **Single LLM choice:** "I used `ChatOpenAI` for both generation and critic scoring — one API key, simpler cost tracking for a portfolio project. LangChain's model interface is provider-agnostic, so adding a second model later — say, routing hard cases to a stronger model — is a one-node addition to the graph, not a rewrite of the pipeline."

> **Implementation Update (2026-07-10):** Talking point should now reference the `core/llm.py` factory pattern: "I built a central `get_llm()` / `get_embeddings()` factory that reads the provider from `.env`. Swapping from OpenAI to Google Gemini was a single env var change — zero code edits in the pipeline nodes."

- **WebSockets:** "I have two WebSocket channels — one for response status, one for vote status. The vote channel intentionally only broadcasts a count, not rankings, so the leaderboard stays blurred until the timer hits zero. Both channels are served by the same FastAPI connection manager."

- **Ranked-choice:** "I implemented instant-runoff voting from scratch — clean algorithm, deterministic, easy to unit test. It avoids vote splitting, which is exactly the right property for a 3-option group decision."

- **Organiser recovery:** "In the first version, the organiser had no durable identity — just a browser tab. Losing it meant losing the trip permanently, and it was also the hidden dependency behind participant link recovery, since the organiser's own WhatsApp history was the only fallback. I fixed this by giving each trip a `management_token` — separate from participant tokens, never expires — plus a one-field email recovery flow through Resend. I deliberately skipped full OAuth here: the actual failure mode was 'I lost my link,' not 'I need to prove who I am,' so a durable token plus a resend-by-email path solves the real problem without adding a login system the rest of the app doesn't need."
