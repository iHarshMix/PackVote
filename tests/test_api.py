from fastapi.testclient import TestClient
from packvote.backend.main import app

client = TestClient(app)

def test_create_trip():
    response = client.post("/trips", json={
        "name": "Goa Trip",
        "dates_rough": "Next weekend",
        "participant_count": 5,
        "organiser_email": "org@example.com"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Goa Trip"
    assert "management_token" in data
