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
    participants: list[ParticipantOut]

class ForceCloseRequest(BaseModel):

    management_token: UUID

class ForceCloseResponse(BaseModel):
    ok: bool
    responses_received: int
    total_participants: int

class OpenVoteRequest(BaseModel):
    """POST /trips/{id}/open-vote — organiser starts the voting phase."""
    management_token: UUID
    vote_duration_hours: int = 12     # default 12-hour countdown

class RevealOut(BaseModel):
    """GET /trips/{id}/reveal response — aggregated preferences + AI recommendations."""
    aggregated: dict
    recommendations: list[RecommendationOut]

class ResultOut(BaseModel):
    """GET /trips/{id}/result response — final winner + vote breakdown."""
    winner: str
    vote_breakdown: dict      # {"Goa": 3, "Coorg": 1, "Kasol": 1}
    ai_summary: str           # one-line AI-generated summary of why the winner won

class ParticipantValidateOut(BaseModel):
    """GET /participants/validate/{token} response."""
    participant_id: UUID
    participant_name: str
    trip_id: UUID
    trip_status: str
    responded: bool
    voted: bool


# ── Structured LLM Output schemas ───────────────────────────────────────────

class RecommendationsOutput(BaseModel):
    recommendations: list[RecommendationOut]


class CriticOutput(BaseModel):
    score: float
    feedback: str
