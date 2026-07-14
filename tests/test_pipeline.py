import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from packvote.backend.core.database import SessionLocal
from packvote.backend.models.db import Trip, Participant, Response, Destination, Recommendation
from packvote.backend.pipeline.nodes.aggregate import aggregate_node
from packvote.backend.pipeline.nodes.retrieve import retrieve_node
from packvote.backend.pipeline.nodes.recommend import recommend_node
from packvote.backend.pipeline.nodes.critic import critic_node, should_retry
from packvote.backend.pipeline.graph import pipeline
from packvote.shared.schemas import RecommendationsOutput, RecommendationOut, CriticOutput
from packvote.backend.core.config import settings

def test_aggregate_node_success():
    # Setup test trip
    with SessionLocal() as db:
        trip = Trip(name="Test Aggregate Trip", organiser_email="test@org.com", dates_rough="Next month")
        db.add(trip)
        db.flush()
        
        p1 = Participant(trip_id=trip.id, name="User 1")
        p2 = Participant(trip_id=trip.id, name="User 2")
        db.add_all([p1, p2])
        db.flush()
        
        # Seed destinations so vibe check doesn't fail
        d1 = Destination(name="Goa", vibe_tags=["beach", "relax"], budget_low=5000, budget_high=15000, best_months=[], activities=[])
        d2 = Destination(name="Manali", vibe_tags=["mountains", "adventure"], budget_low=8000, budget_high=20000, best_months=[], activities=[])
        db.add_all([d1, d2])
        db.flush()
        
        r1 = Response(
            participant_id=p1.id,
            trip_id=trip.id,
            swipes=[{"destination": "Goa", "liked": True}, {"destination": "Manali", "liked": False}],
            budget_max=10000,
            unavailable_dates=["2026-08-01", "2026-08-02"]
        )
        r2 = Response(
            participant_id=p2.id,
            trip_id=trip.id,
            swipes=[{"destination": "Goa", "liked": True}, {"destination": "Manali", "liked": True}],
            budget_max=12000,
            unavailable_dates=["2026-08-02", "2026-08-03"]
        )
        db.add_all([r1, r2])
        db.commit()
        
        trip_id = trip.id
    
    state = {
        "trip_id": str(trip_id),
        "prompt_version": "v1",
        "responses": [],
        "aggregated": {},
        "retrieved_destinations": [],
        "recommendations": [],
        "critic_score": 0.0,
        "critic_feedback": "",
        "retry_count": 0
    }
    
    # Run node
    new_state = aggregate_node(state)
    
    # Assertions
    agg = new_state["aggregated"]
    assert agg["top_destinations"] == ["Goa", "Manali"]
    assert agg["budget_sweet_spot"] == 11000  # median of 10000 and 12000
    assert set(agg["vibe_overlap"]).issubset({"beach", "relax", "mountains", "adventure"})
    assert agg["date_conflicts"] == ["2026-08-01", "2026-08-02", "2026-08-03"]
    assert len(new_state["responses"]) == 2

@patch("packvote.backend.pipeline.nodes.retrieve.get_embeddings")
def test_retrieve_node_success(mock_get_embeddings):
    # Mock embeddings output
    mock_emb = MagicMock()
    mock_emb.embed_query.return_value = [0.1] * settings.embedding_dimension
    mock_get_embeddings.return_value = mock_emb

    # Seed destination
    with SessionLocal() as db:
        # Clear existing to ensure we get our seeded one
        db.query(Destination).delete()
        d = Destination(
            name="Seeded Destination",
            vibe_tags=["chill"],
            budget_low=2000,
            budget_high=8000,
            best_months=["Jan"],
            activities=["hiking"],
            embedding=[0.1] * settings.embedding_dimension
        )
        db.add(d)
        db.commit()

    state = {
        "trip_id": str(uuid4()),
        "prompt_version": "v1",
        "responses": [],
        "aggregated": {
            "top_destinations": [],
            "budget_sweet_spot": 5000,
            "vibe_overlap": ["chill"],
            "date_conflicts": []
        },
        "retrieved_destinations": [],
        "recommendations": [],
        "critic_score": 0.0,
        "critic_feedback": "",
        "retry_count": 0
    }

    new_state = retrieve_node(state)
    assert len(new_state["retrieved_destinations"]) > 0
    assert new_state["retrieved_destinations"][0]["name"] == "Seeded Destination"

@patch("packvote.backend.pipeline.nodes.recommend.get_llm")
def test_recommend_node_success(mock_get_llm):
    mock_llm_instance = MagicMock()
    mock_chain = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_chain
    mock_get_llm.return_value = mock_llm_instance

    mock_recs = RecommendationsOutput(
        recommendations=[
            RecommendationOut(destination="Goa", fit_reason="Good", tradeoff="None", budget_estimate=12000)
        ]
    )
    mock_chain.invoke.return_value = mock_recs
    mock_chain.return_value = mock_recs

    state = {
        "trip_id": str(uuid4()),
        "prompt_version": "v1",
        "responses": [],
        "aggregated": {
            "top_destinations": [],
            "budget_sweet_spot": 10000,
            "vibe_overlap": [],
            "date_conflicts": []
        },
        "retrieved_destinations": [],
        "recommendations": [],
        "critic_score": 0.0,
        "critic_feedback": "",
        "retry_count": 0
    }

    new_state = recommend_node(state)
    assert len(new_state["recommendations"]) == 1
    assert new_state["recommendations"][0]["destination"] == "Goa"

@patch("packvote.backend.pipeline.nodes.critic.get_llm")
def test_critic_node_and_retry_logic(mock_get_llm):
    mock_llm_instance = MagicMock()
    mock_chain = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_chain
    mock_get_llm.return_value = mock_llm_instance

    # 1. Critic score < 0.7 (causes retry)
    mock_critic_output = CriticOutput(score=0.5, feedback="Improve vibe citation")
    mock_chain.invoke.return_value = mock_critic_output
    mock_chain.return_value = mock_critic_output
    state = {
        "trip_id": str(uuid4()),
        "prompt_version": "v1",
        "responses": [],
        "aggregated": {},
        "retrieved_destinations": [],
        "recommendations": [],
        "critic_score": 0.0,
        "critic_feedback": "",
        "retry_count": 0
    }

    state = critic_node(state)
    assert state["critic_score"] == 0.5
    assert should_retry(state) == "retry"
    assert state["retry_count"] == 1

    # 2. Score still < 0.7, but retry limit reached
    state = critic_node(state)
    assert should_retry(state) == "retry"
    assert state["retry_count"] == 2

    # Third time should fall through to "output" (capping at 2 retries)
    assert should_retry(state) == "output"

    # 3. Critic score >= 0.7 (no retry)
    mock_critic_output_ok = CriticOutput(score=0.9, feedback="Perfect")
    mock_chain.invoke.return_value = mock_critic_output_ok
    mock_chain.return_value = mock_critic_output_ok
    state["retry_count"] = 0
    state = critic_node(state)
    assert should_retry(state) == "output"

@patch("packvote.backend.pipeline.nodes.retrieve.get_embeddings")
@patch("packvote.backend.pipeline.nodes.recommend.get_llm")
@patch("packvote.backend.pipeline.nodes.critic.get_llm")
def test_pipeline_integration_end_to_end(mock_critic_llm, mock_rec_llm, mock_get_embeddings):
    # Setup mocks
    # Embeddings
    mock_emb = MagicMock()
    mock_emb.embed_query.return_value = [0.1] * settings.embedding_dimension
    mock_get_embeddings.return_value = mock_emb

    # Rec LLM
    mock_rec_llm_inst = MagicMock()
    mock_rec_chain = MagicMock()
    mock_rec_llm_inst.with_structured_output.return_value = mock_rec_chain
    mock_rec_llm.return_value = mock_rec_llm_inst
    mock_recs_int = RecommendationsOutput(
        recommendations=[
            RecommendationOut(destination="Goa", fit_reason="Match", tradeoff="None", budget_estimate=15000)
        ]
    )
    mock_rec_chain.invoke.return_value = mock_recs_int
    mock_rec_chain.return_value = mock_recs_int

    # Critic LLM (return high score first try to avoid infinite loop)
    mock_crit_llm_inst = MagicMock()
    mock_crit_chain = MagicMock()
    mock_crit_llm_inst.with_structured_output.return_value = mock_crit_chain
    mock_critic_llm.return_value = mock_crit_llm_inst
    mock_crit_output_int = CriticOutput(score=0.8, feedback="Acceptable")
    mock_crit_chain.invoke.return_value = mock_crit_output_int
    mock_crit_chain.return_value = mock_crit_output_int

    # Seed DB
    with SessionLocal() as db:
        trip = Trip(name="Integration Test Trip", organiser_email="test@integration.com", dates_rough="Next month")
        db.add(trip)
        db.flush()

        p1 = Participant(trip_id=trip.id, name="User 1")
        db.add(p1)
        db.flush()

        d = Destination(
            name="Goa",
            vibe_tags=["beach"],
            budget_low=10000,
            budget_high=20000,
            best_months=[],
            activities=[],
            embedding=[0.1] * settings.embedding_dimension
        )
        db.add(d)
        db.flush()

        r = Response(
            participant_id=p1.id,
            trip_id=trip.id,
            swipes=[{"destination": "Goa", "liked": True}],
            budget_max=15000,
            unavailable_dates=[]
        )
        db.add(r)
        db.commit()

        trip_id = trip.id

    initial_state = {
        "trip_id": str(trip_id),
        "prompt_version": "v1",
        "responses": [],
        "aggregated": {},
        "retrieved_destinations": [],
        "recommendations": [],
        "critic_score": 0.0,
        "critic_feedback": "",
        "retry_count": 0
    }

    final_state = pipeline.invoke(initial_state)

    assert final_state["critic_score"] == 0.8
    assert len(final_state["recommendations"]) == 1
    assert final_state["recommendations"][0]["destination"] == "Goa"
