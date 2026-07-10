import pytest
from fastapi.testclient import TestClient
from packvote.backend.main import app

from packvote.backend.core.database import SessionLocal
from packvote.backend.models.db import Trip, TripStatus

client = TestClient(app)

def test_survey_endpoints():
    # 1. Create Trip
    trip_resp = client.post("/trips", json={
        "name": "Test Survey Trip",
        "dates_rough": "Next week",
        "participant_count": 2,
        "organiser_email": "org@example.com"
    })
    assert trip_resp.status_code == 201
    trip_data = trip_resp.json()
    trip_id = trip_data["id"]
    management_token = trip_data["management_token"]

    # 2. Add Participants
    part_resp = client.post(f"/trips/{trip_id}/participants", json={
        "count": 2
    })
    assert part_resp.status_code == 200
    participants = part_resp.json()
    p1_token = participants[0]["unique_token"]
    p2_token = participants[1]["unique_token"]

    # 3. Check status
    status_resp = client.get(f"/trips/{trip_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "setup"

    # 4. Try submitting response in setup phase (should fail due to status guard)
    fail_resp = client.post("/responses", json={
        "participant_token": p1_token,
        "swipes": [{"destination": "Goa", "liked": True}],
        "budget_max": 500,
        "unavailable_dates": []
    })
    assert fail_resp.status_code == 400
    assert "not in survey phase" in fail_resp.json()["detail"]

    # Manually transition to survey phase for testing
    with SessionLocal() as db_session:
        db_trip = db_session.query(Trip).filter(Trip.id == trip_id).first()
        db_trip.status = TripStatus.survey
        db_session.commit()

    # 5. Submit valid response
    valid_resp = client.post("/responses", json={
        "participant_token": p1_token,
        "swipes": [{"destination": "Goa", "liked": True}],
        "budget_max": 500,
        "unavailable_dates": ["2023-12-01"]
    })
    assert valid_resp.status_code == 200
    assert valid_resp.json()["message"] == "Response recorded"

    # 6. Submit again (should fail)
    duplicate_resp = client.post("/responses", json={
        "participant_token": p1_token,
        "swipes": [{"destination": "Goa", "liked": True}],
        "budget_max": 500,
        "unavailable_dates": []
    })
    assert duplicate_resp.status_code == 400
    assert "already responded" in duplicate_resp.json()["detail"]

    # 7. Force close survey
    force_close_resp = client.post(f"/trips/{trip_id}/force-close", json={
        "management_token": management_token
    })
    assert force_close_resp.status_code == 200
    assert force_close_resp.json()["ok"] == True
    assert force_close_resp.json()["responses_received"] == 1
    assert force_close_resp.json()["total_participants"] == 3 # 2 + 1 organiser
