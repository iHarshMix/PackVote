from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel
from packvote.backend.core.database import get_db
from packvote.backend.models.db import Trip, Participant, TripStatus
from packvote.shared.schemas import TripCreate, TripOut, ParticipantOut
from packvote.backend.core.config import settings

router = APIRouter(tags=["trips"])

class ParticipantCreate(BaseModel):
    count: int

def to_participant_out(participant: Participant) -> ParticipantOut:
    return ParticipantOut(
        id=participant.id,
        name=participant.name,
        unique_token=participant.unique_token,
        survey_url=f"{settings.frontend_url}/survey?token={participant.unique_token}",
    )

@router.post("/trips", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, db: Session = Depends(get_db)):
    new_trip = Trip(
        name=payload.name,
        organiser_email=payload.organiser_email,
        dates_rough=payload.dates_rough,
        status=TripStatus.setup
    )
    db.add(new_trip)
    db.flush()

    # Create organiser
    organiser = Participant(
        trip_id=new_trip.id,
        name="Organiser",
        is_organiser=True
    )
    db.add(organiser)
    db.commit()
    db.refresh(new_trip)

    return TripOut(
        id=new_trip.id,
        name=new_trip.name,
        status=new_trip.status.value,
        management_token=new_trip.management_token,
        created_at=new_trip.created_at
    )

@router.post("/trips/{trip_id}/participants", response_model=list[ParticipantOut])
def create_participants(trip_id: UUID, payload: ParticipantCreate, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
        
    participants = []
    for i in range(payload.count):
        p = Participant(
            trip_id=trip.id,
            name=f"Participant {i+1}",
            is_organiser=False
        )
        db.add(p)
        participants.append(p)
    
    db.commit()
    for p in participants:
        db.refresh(p)
        
    return [to_participant_out(p) for p in participants]
