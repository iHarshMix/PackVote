"""End-to-end integration tests for the PackVote application."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from packvote.backend.main import app
from packvote.backend.core.database import SessionLocal
from packvote.backend.models.db import Destination, Trip, Participant, Vote, Response as DBResponse, Recommendation
from packvote.backend.core.config import settings
from packvote.shared.schemas import RecommendationsOutput, RecommendationOut, CriticOutput

client = TestClient(app)


@patch("packvote.backend.pipeline.nodes.retrieve.get_embeddings")
@patch("packvote.backend.pipeline.nodes.recommend.get_llm")
@patch("packvote.backend.pipeline.nodes.critic.get_llm")
@patch("packvote.backend.core.llm.get_llm")
def test_full_trip_e2e_flow(
    mock_get_core_llm,
    mock_crit_llm,
    mock_rec_llm,
    mock_get_embeddings,
):
    # ── 1. Seed destinations in database for RAG ───────────────────────────
    with SessionLocal() as db:
        db.query(Vote).delete()
        db.query(DBResponse).delete()
        db.query(Recommendation).delete()
        db.query(Participant).delete()
        db.query(Trip).delete()
        db.query(Destination).delete()
        db.commit()

        d1 = Destination(
            name="Goa",
            vibe_tags=["beach", "party"],
            budget_low=10000,
            budget_high=30000,
            best_months=["December"],
            activities=["sunbathing"],
            embedding=[0.1] * settings.embedding_dimension,
        )
        d2 = Destination(
            name="Manali",
            vibe_tags=["mountains", "adventure"],
            budget_low=15000,
            budget_high=40000,
            best_months=["January"],
            activities=["trekking"],
            embedding=[0.1] * settings.embedding_dimension,
        )
        d3 = Destination(
            name="Coorg",
            vibe_tags=["nature", "quiet"],
            budget_low=12000,
            budget_high=35000,
            best_months=["October"],
            activities=["relaxing"],
            embedding=[0.1] * settings.embedding_dimension,
        )
        db.add_all([d1, d2, d3])
        db.commit()

    # ── 2. Mock Embeddings and LLMs ──────────────────────────────────────────
    # Embeddings
    mock_emb = MagicMock()
    mock_emb.embed_query.return_value = [0.1] * settings.embedding_dimension
    mock_get_embeddings.return_value = mock_emb

    # Recommendation Node LLM (Rule 8: set invoke.return_value and return_value)
    mock_rec_llm_inst = MagicMock()
    mock_rec_chain = MagicMock()
    mock_rec_llm_inst.with_structured_output.return_value = mock_rec_chain
    mock_rec_llm.return_value = mock_rec_llm_inst
    mock_recs_out = RecommendationsOutput(
        recommendations=[
            RecommendationOut(destination="Goa", fit_reason="Beach vibe", tradeoff="Crowded", budget_estimate=15000),
            RecommendationOut(destination="Manali", fit_reason="Snow mountains", tradeoff="Cold", budget_estimate=25000),
            RecommendationOut(destination="Coorg", fit_reason="Hills & coffee", tradeoff="Rainy", budget_estimate=12000),
        ]
    )
    mock_rec_chain.invoke.return_value = mock_recs_out
    mock_rec_chain.return_value = mock_recs_out

    # Critic Node LLM
    mock_crit_llm_inst = MagicMock()
    mock_crit_chain = MagicMock()
    mock_crit_llm_inst.with_structured_output.return_value = mock_crit_chain
    mock_crit_llm.return_value = mock_crit_llm_inst
    mock_crit_output = CriticOutput(score=0.9, feedback="Looks solid")
    mock_crit_chain.invoke.return_value = mock_crit_output
    mock_crit_chain.return_value = mock_crit_output

    # Core LLM for AI Summary
    mock_core_llm = MagicMock()
    mock_core_llm.invoke.return_value.content = "Goa won because the group loves beach parties and sweet spot budget match!"
    mock_core_llm.return_value.content = "Goa won because the group loves beach parties and sweet spot budget match!"
    mock_get_core_llm.return_value = mock_core_llm

    # ── 3. Start the flow: Create a trip (Setup Phase) ──────────────────────
    trip_resp = client.post("/trips", json={
        "name": "E2E Group Trip",
        "organiser_email": "organiser@e2e.com",
        "dates_rough": "December 2026",
        "participant_count": 2,
    })
    assert trip_resp.status_code == 201
    trip_data = trip_resp.json()
    trip_id = trip_data["id"]
    management_token = trip_data["management_token"]
    assert trip_data["status"] == "setup"

    # Add 2 more participants (making 3 total: 1 organiser + 2 participants)
    participants_resp = client.post(f"/trips/{trip_id}/participants", json={
        "count": 2,
    })
    assert participants_resp.status_code == 200
    participants_data = participants_resp.json()
    assert len(participants_data) == 2

    # Query all participants to get tokens
    with SessionLocal() as db:
        db_participants = db.query(Participant).filter(Participant.trip_id == trip_id).all()
        assert len(db_participants) == 3
        # Extract the tokens and names
        tokens = {p.name: p.unique_token for p in db_participants}

    # Verify status is setup
    status_resp = client.get(f"/trips/{trip_id}/status")
    assert status_resp.json()["status"] == "setup"

    # Verify validation endpoint before survey starts
    val_resp = client.get(f"/participants/validate/{tokens['Organiser']}")
    assert val_resp.status_code == 200
    assert val_resp.json()["trip_status"] == "setup"

    # ── 4. Open survey phase ────────────────────────────────────────────────
    start_survey_resp = client.post(f"/trips/{trip_id}/start-survey")
    assert start_survey_resp.status_code == 200
    assert start_survey_resp.json()["status"] == "survey"

    # Verify validation endpoint now says survey
    val_resp = client.get(f"/participants/validate/{tokens['Organiser']}")
    assert val_resp.json()["trip_status"] == "survey"
    assert val_resp.json()["responded"] is False

    # ── 5. Submit survey responses for all 3 participants ───────────────────
    # Participant 1 swipes Goa & Manali, max budget 20k
    r1 = client.post("/responses", json={
        "participant_token": str(tokens["Participant 1"]),
        "swipes": [
            {"destination": "Goa", "liked": True},
            {"destination": "Manali", "liked": True},
            {"destination": "Coorg", "liked": False},
        ],
        "budget_max": 20000,
        "unavailable_dates": ["2026-12-25"],
    })
    assert r1.status_code == 200

    # Participant 2 swipes Goa & Coorg, max budget 25k
    r2 = client.post("/responses", json={
        "participant_token": str(tokens["Participant 2"]),
        "swipes": [
            {"destination": "Goa", "liked": True},
            {"destination": "Manali", "liked": False},
            {"destination": "Coorg", "liked": True},
        ],
        "budget_max": 25000,
        "unavailable_dates": [],
    })
    assert r2.status_code == 200

    # Organiser swipes all, max budget 30k
    r3 = client.post("/responses", json={
        "participant_token": str(tokens["Organiser"]),
        "swipes": [
            {"destination": "Goa", "liked": True},
            {"destination": "Manali", "liked": True},
            {"destination": "Coorg", "liked": True},
        ],
        "budget_max": 30000,
        "unavailable_dates": ["2026-12-24"],
    })
    assert r3.status_code == 200

    # ── 6. Check automatic pipeline transition to Reveal ───────────────────
    # Since 3/3 responded, status should now be 'reveal'
    status_resp = client.get(f"/trips/{trip_id}/status")
    assert status_resp.json()["status"] == "reveal"

    # Retrieve preferences reveal
    reveal_resp = client.get(f"/trips/{trip_id}/reveal")
    assert reveal_resp.status_code == 200
    reveal_data = reveal_resp.json()
    
    # Assert aggregated preferences calculations
    agg = reveal_data["aggregated"]
    assert agg["top_destinations"] == ["Goa", "Manali", "Coorg"]
    assert agg["budget_sweet_spot"] == 25000  # median of [20000, 25000, 30000]
    assert agg["date_conflicts"] == ["2026-12-24", "2026-12-25"]
    assert len(reveal_data["recommendations"]) == 3
    assert reveal_data["recommendations"][0]["destination"] == "Goa"

    # ── 7. Start voting phase (Organiser Action) ────────────────────────────
    open_vote_resp = client.post(f"/trips/{trip_id}/open-vote", json={
        "management_token": management_token,
        "vote_duration_hours": 12,
    })
    assert open_vote_resp.status_code == 200
    assert open_vote_resp.json()["status"] == "voting"

    # ── 8. Cast ballots for all participants ────────────────────────────────
    # Participant 1 ranks: Goa > Coorg > Manali
    v1 = client.post("/votes", json={
        "participant_token": str(tokens["Participant 1"]),
        "ranking": ["Goa", "Coorg", "Manali"],
    })
    assert v1.status_code == 200

    # Participant 2 ranks: Coorg > Goa > Manali
    v2 = client.post("/votes", json={
        "participant_token": str(tokens["Participant 2"]),
        "ranking": ["Coorg", "Goa", "Manali"],
    })
    assert v2.status_code == 200

    # Organiser ranks: Goa > Manali > Coorg
    v3 = client.post("/votes", json={
        "participant_token": str(tokens["Organiser"]),
        "ranking": ["Goa", "Manali", "Coorg"],
    })
    assert v3.status_code == 200

    # ── 9. Fetch results (Complete Phase) ───────────────────────────────────
    # Since 3/3 voted, fetching result should transition to complete and return winner
    result_resp = client.get(f"/trips/{trip_id}/result")
    assert result_resp.status_code == 200
    result_data = result_resp.json()

    # Tally assert: Goa had 2 first-place votes, Coorg had 1. Goa wins.
    assert result_data["winner"] == "Goa"
    assert result_data["vote_breakdown"] == {"Goa": 2, "Coorg": 1, "Manali": 0}
    assert result_data["ai_summary"] == "Goa won because the group loves beach parties and sweet spot budget match!"

    # Verify status is complete
    status_resp = client.get(f"/trips/{trip_id}/status")
    assert status_resp.json()["status"] == "complete"

    # Call result endpoint again to verify caching works
    cached_resp = client.get(f"/trips/{trip_id}/result")
    assert cached_resp.status_code == 200
    assert cached_resp.json()["winner"] == "Goa"
