from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from packvote.backend.core.database import get_db
from packvote.backend.models.db import Trip, Participant, TripStatus
from packvote.shared.schemas import TripCreate, TripOut, ParticipantOut, OpenVoteRequest
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

@router.post("/trips/{trip_id}/start-survey", response_model=TripOut)
def start_survey(trip_id: UUID, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != TripStatus.setup:
        raise HTTPException(status_code=400, detail="Trip is not in setup phase")
    
    trip.status = TripStatus.survey
    db.commit()
    db.refresh(trip)
    
    return TripOut(
        id=trip.id,
        name=trip.name,
        status=trip.status.value,
        management_token=trip.management_token,
        created_at=trip.created_at
    )

@router.post("/trips/{trip_id}/open-vote")
def open_vote(trip_id: UUID, payload: OpenVoteRequest, db: Session = Depends(get_db)):
    """Transition trip from reveal → voting and set the vote deadline."""
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.management_token == payload.management_token).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found or invalid management token")
    if trip.status != TripStatus.reveal:
        raise HTTPException(status_code=409, detail="Trip is not in reveal phase — cannot open voting yet")

    trip.status = TripStatus.voting
    trip.vote_deadline = datetime.now(timezone.utc) + timedelta(hours=payload.vote_duration_hours)
    db.commit()

    return {"status": "voting", "vote_deadline": trip.vote_deadline.isoformat()}

