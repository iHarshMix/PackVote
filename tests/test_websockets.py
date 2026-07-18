import pytest
from fastapi.testclient import TestClient
from packvote.backend.main import app
from packvote.backend.core.database import SessionLocal
from packvote.backend.models.db import Trip, TripStatus

client = TestClient(app)

def test_websocket_broadcast_on_response():
    # 1. Create Trip
    trip_resp = client.post("/trips", json={
        "name": "WS Test Trip",
        "dates_rough": "November 2026",
        "participant_count": 2,
        "organiser_email": "org@ws.com"
    })
    assert trip_resp.status_code == 201
    trip_data = trip_resp.json()
    trip_id = trip_data["id"]
    
    # 2. Add Participant
    part_resp = client.post(f"/trips/{trip_id}/participants", json={
        "count": 1
    })
    assert part_resp.status_code == 200
    participants = part_resp.json()
    p_token = participants[0]["unique_token"]
    
    # 3. Transition status to survey
    start_resp = client.post(f"/trips/{trip_id}/start-survey")
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "survey"

    # 4. Connect to WebSocket status channel
    with client.websocket_connect(f"/ws/{trip_id}/status") as websocket:
        # 5. Submit response
        response_payload = {
            "participant_token": p_token,
            "swipes": [{"destination": "Goa", "liked": True}],
            "budget_max": 20000,
            "unavailable_dates": []
        }
        resp = client.post("/responses", json=response_payload)
        assert resp.status_code == 200
        
        # 6. Receive status broadcast from WebSocket
        data = websocket.receive_json()
        assert data["type"] == "status_update"
        assert data["trip_id"] == trip_id
        assert data["status"] == "survey"
        assert data["responded_count"] == 1
        assert data["total_count"] == 2
        assert len(data["participants"]) == 2
        
        # One is Organiser, one is Participant 1
        names = {p["name"] for p in data["participants"]}
        assert "Organiser" in names
        assert "Participant 1" in names
