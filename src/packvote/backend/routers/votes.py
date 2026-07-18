from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
import asyncio
import logging

from packvote.backend.core.database import get_db
from packvote.backend.models.db import Trip, Participant, Vote, TripStatus
from packvote.shared.schemas import VoteSubmit
from packvote.backend.websockets.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["votes"])


@router.post("/votes", status_code=status.HTTP_200_OK)
async def submit_vote(payload: VoteSubmit, db: Session = Depends(get_db)):
    """Submit a ranked-choice ballot for a participant."""
    # 1. Validate participant token
    participant = db.query(Participant).filter(
        Participant.unique_token == payload.participant_token
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    trip = db.query(Trip).filter(Trip.id == participant.trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # 2. Status guard — only accept votes during voting phase
    if trip.status != TripStatus.voting:
        raise HTTPException(status_code=409, detail="Trip is not in voting phase")

    # 3. Prevent double voting
    if participant.voted:
        raise HTTPException(status_code=400, detail="Participant has already voted")

    # 4. Save the ballot
    vote = Vote(
        participant_id=participant.id,
        trip_id=trip.id,
        ranking=payload.ranking,
    )
    db.add(vote)
    participant.voted = True
    db.commit()

    # 5. Broadcast updated vote count on the vote-status channel
    voted_count = db.query(Participant).filter(
        Participant.trip_id == trip.id,
        Participant.voted == True,
    ).count()
    total_count = db.query(Participant).filter(
        Participant.trip_id == trip.id,
    ).count()

    channel = f"{trip.id}:vote-status"
    message = {
        "type": "vote_update",
        "trip_id": str(trip.id),
        "voted_count": voted_count,
        "total_count": total_count,
    }
    await manager.broadcast(message, channel)

    return {"message": "Vote recorded", "voted_count": voted_count, "total_count": total_count}
