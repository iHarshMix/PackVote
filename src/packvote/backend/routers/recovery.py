from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from packvote.backend.core.database import get_db
from packvote.backend.models.db import Trip, Participant
from packvote.shared.schemas import TripRecoverRequest, TripManageOut, ParticipantOut
from packvote.backend.core.config import settings
from packvote.backend.core.email import send_management_link

router = APIRouter(tags=["recovery"])

def to_participant_out(participant: Participant) -> ParticipantOut:
    return ParticipantOut(
        id=participant.id,
        name=participant.name,
        unique_token=participant.unique_token,
        survey_url=f"{settings.frontend_url}/survey?token={participant.unique_token}"
    )

@router.get("/trips/manage/{management_token}", response_model=TripManageOut)
def get_trip_management_data(management_token: UUID, db: Session = Depends(get_db)):
    """Fetches the full management view of a trip, including all participant survey URLs."""
    trip = db.query(Trip).filter(Trip.management_token == management_token).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found with this management token")

    participants = db.query(Participant).filter(Participant.trip_id == trip.id).order_by(Participant.created_at).all()
    
    return TripManageOut(
        id=trip.id,
        name=trip.name,
        status=trip.status.value,
        participants=[to_participant_out(p) for p in participants]
    )

@router.post("/trips/recover", status_code=status.HTTP_200_OK)
def recover_trips(payload: TripRecoverRequest, db: Session = Depends(get_db)):
    """Looks up trips associated with the email and sends recovery emails. Returns success regardless."""
    trips = db.query(Trip).filter(Trip.organiser_email == payload.email).all()
    for trip in trips:
        try:
            send_management_link(
                to_email=payload.email,
                trip_name=trip.name,
                management_token=str(trip.management_token)
            )
        except Exception:
            # Silently log/ignore sending failure for individual email to ensure API is robust and anonymous
            pass
            
    # Always return success to prevent email discovery/enumeration
    return {"sent": True}
