from unittest.mock import patch
from fastapi.testclient import TestClient
from packvote.backend.main import app

client = TestClient(app)

def test_get_trip_management_data():
    # 1. Create a Trip
    trip_resp = client.post("/trips", json={
        "name": "Trip for Management Test",
        "dates_rough": "Next Month",
        "participant_count": 2,
        "organiser_email": "manager@example.com"
    })
    assert trip_resp.status_code == 201
    trip_data = trip_resp.json()
    management_token = trip_data["management_token"]
    trip_id = trip_data["id"]

    # 2. Add Participants so we have links to manage
    part_resp = client.post(f"/trips/{trip_id}/participants", json={
        "count": 2
    })
    assert part_resp.status_code == 200

    # 3. Retrieve management data
    manage_resp = client.get(f"/trips/manage/{management_token}")
    assert manage_resp.status_code == 200
    manage_data = manage_resp.json()
    
    assert manage_data["id"] == trip_id
    assert manage_data["name"] == "Trip for Management Test"
    assert manage_data["status"] == "setup"
    assert len(manage_data["participants"]) == 3  # 2 + 1 organiser
    
    # Check that participant objects contain survey URLs and tokens
    for p in manage_data["participants"]:
        assert "unique_token" in p
        assert "survey_url" in p
        assert p["survey_url"].startswith("http://localhost:8501/survey?token=")

    # 4. Try requesting with invalid token
    fake_token = "00000000-0000-0000-0000-000000000000"
    fail_resp = client.get(f"/trips/manage/{fake_token}")
    assert fail_resp.status_code == 404


@patch("packvote.backend.routers.recovery.send_management_link")
def test_recover_trips(mock_send):
    import uuid
    email = f"testorg_{uuid.uuid4()}@example.com"
    
    # 1. Create a Trip
    trip_resp = client.post("/trips", json={
        "name": "Recovery Trip",
        "dates_rough": "Sometime",
        "participant_count": 1,
        "organiser_email": email
    })
    assert trip_resp.status_code == 201
    trip_data = trip_resp.json()
    management_token = trip_data["management_token"]

    # 2. Trigger Recovery
    recovery_resp = client.post("/trips/recover", json={"email": email})
    assert recovery_resp.status_code == 200
    assert recovery_resp.json() == {"sent": True}

    # Verify that the email utility was called with the correct parameters
    mock_send.assert_called_once_with(
        to_email=email,
        trip_name="Recovery Trip",
        management_token=str(management_token)
    )

    # Reset mock and check with an email that has no trips
    mock_send.reset_mock()
    recovery_resp_empty = client.post("/trips/recover", json={"email": "notrips@example.com"})
    assert recovery_resp_empty.status_code == 200
    assert recovery_resp_empty.json() == {"sent": True}
    
    # Verification email should not be sent for non-existent emails
    mock_send.assert_not_called()
