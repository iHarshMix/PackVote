from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel
import random
import asyncio

import logging
from packvote.backend.core.database import get_db, SessionLocal
from packvote.backend.models.db import Trip, Participant, TripStatus, Response as DBResponse, Recommendation
from packvote.shared.schemas import SurveySubmit, ForceCloseRequest, ForceCloseResponse, ParticipantValidateOut
from packvote.backend.pipeline.graph import pipeline
from packvote.backend.core.config import settings
from packvote.backend.websockets.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["responses"])

async def broadcast_trip_status(trip_id: UUID, db: Session):
    """Fetches full status details of the trip and broadcasts to the status channel."""
    try:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            return
        
        participants = db.query(Participant).filter(Participant.trip_id == trip_id).all()
        total_participants = len(participants)
        responded_participants = sum(1 for p in participants if p.responded)
        
        participant_list = [
            {"name": p.name, "responded": p.responded}
            for p in participants
        ]
        
        message = {
            "type": "status_update",
            "trip_id": str(trip_id),
            "status": trip.status.value,
            "responded_count": responded_participants,
            "total_count": total_participants,
            "participants": participant_list
        }
        
        channel = f"{trip_id}:status"
        await manager.broadcast(message, channel)
    except Exception as e:
        logger.error(f"Failed to broadcast status update for trip {trip_id}: {e}", exc_info=True)

def broadcast_status_sync(trip_id: UUID):
    """Thread-safe synchronous wrapper to broadcast status from background threads."""
    try:
        with SessionLocal() as db:
            trip = db.query(Trip).filter(Trip.id == trip_id).first()
            if not trip:
                return
            participants = db.query(Participant).filter(Participant.trip_id == trip_id).all()
            total_participants = len(participants)
            responded_participants = sum(1 for p in participants if p.responded)
            participant_list = [{"name": p.name, "responded": p.responded} for p in participants]
            
            message = {
                "type": "status_update",
                "trip_id": str(trip_id),
                "status": trip.status.value,
                "responded_count": responded_participants,
                "total_count": total_participants,
                "participants": participant_list
            }
        
        channel = f"{trip_id}:status"
        loop = asyncio.new_event_loop()
        loop.run_until_complete(manager.broadcast(message, channel))
        loop.close()
    except Exception as e:
        logger.error(f"Error in sync status broadcast for trip {trip_id}: {e}", exc_info=True)

def trigger_pipeline(trip_id: UUID, prompt_version: str):
    logger.info(f"Triggering LangGraph pipeline for trip {trip_id} (prompt version: {prompt_version})")
    
    initial_state = {
        "trip_id": str(trip_id),
        "prompt_version": prompt_version,
        "responses": [],
        "aggregated": {},
        "retrieved_destinations": [],
        "recommendations": [],
        "critic_score": 0.0,
        "critic_feedback": "",
        "retry_count": 0
    }
    
    try:
        final_state = pipeline.invoke(initial_state)
        
        with SessionLocal() as db:
            # Clear any existing recommendations for this trip for idempotency
            db.query(Recommendation).filter(Recommendation.trip_id == trip_id).delete()
            
            # Save the new recommendations
            for idx, rec_dict in enumerate(final_state.get("recommendations", []), start=1):
                db.add(Recommendation(
                    trip_id=trip_id,
                    destination=rec_dict["destination"],
                    fit_reason=rec_dict["fit_reason"],
                    tradeoff=rec_dict["tradeoff"],
                    budget_estimate=rec_dict["budget_estimate"],
                    rank=idx,
                    prompt_version=prompt_version,
                    model_used=settings.llm_model
                ))
            
            # Transition trip status to reveal
            trip = db.query(Trip).filter(Trip.id == trip_id).first()
            if trip:
                trip.status = TripStatus.reveal
            
            db.commit()
            logger.info(f"LangGraph pipeline succeeded for trip {trip_id}. Generated {len(final_state.get('recommendations', []))} recommendations and transitioned status to reveal.")
            
            # Broadcast the updated status to all dashboard clients
            broadcast_status_sync(trip_id)
            
    except Exception as e:
        logger.error(f"Error running LangGraph pipeline for trip {trip_id}: {e}", exc_info=True)


@router.post("/responses", status_code=status.HTTP_200_OK)
async def submit_response(
    payload: SurveySubmit, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 1. Validate token
    participant = db.query(Participant).filter(Participant.unique_token == payload.participant_token).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
        
    trip = db.query(Trip).filter(Trip.id == participant.trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # 2. Status guard
    if trip.status != TripStatus.survey:
        raise HTTPException(status_code=400, detail="Trip is not in survey phase")

    if participant.responded:
        raise HTTPException(status_code=400, detail="Participant already responded")

    # 3. Save response
    new_response = DBResponse(
        participant_id=participant.id,
        trip_id=trip.id,
        swipes=[s.model_dump() for s in payload.swipes],
        budget_max=payload.budget_max,
        unavailable_dates=payload.unavailable_dates
    )
    db.add(new_response)
    
    # Update participant
    participant.responded = True
    db.commit()

    # 4. Check if everyone responded
    total_participants = db.query(Participant).filter(Participant.trip_id == trip.id).count()
    responded_participants = db.query(Participant).filter(Participant.trip_id == trip.id, Participant.responded).count()

    if responded_participants >= total_participants:
        trip.status = TripStatus.reveal
        db.commit()

        # A/B prompt_version coin flip
        prompt_version = "v1" if random.random() > 0.5 else "v2"
        background_tasks.add_task(trigger_pipeline, trip.id, prompt_version)

    # Broadcast updated counts and state via WebSocket
    await broadcast_trip_status(trip.id, db)

    return {"message": "Response recorded"}

class TripStatusOut(BaseModel):
    status: str

@router.get("/trips/{trip_id}/status", response_model=TripStatusOut)
def get_trip_status(trip_id: UUID, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return TripStatusOut(status=trip.status.value)

# New endpoint for initial dashboard status details
class TripDashboardOut(BaseModel):
    status: str
    responded_count: int
    total_count: int
    participants: list

@router.get("/trips/{trip_id}/dashboard", response_model=TripDashboardOut)
def get_trip_dashboard(trip_id: UUID, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    participants = db.query(Participant).filter(Participant.trip_id == trip_id).all()
    total_participants = len(participants)
    responded_participants = sum(1 for p in participants if p.responded)
    
    return TripDashboardOut(
        status=trip.status.value,
        responded_count=responded_participants,
        total_count=total_participants,
        participants=[{"name": p.name, "responded": p.responded} for p in participants]
    )

@router.post("/trips/{trip_id}/force-close", response_model=ForceCloseResponse)
async def force_close_survey(
    trip_id: UUID, 
    payload: ForceCloseRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
        
    if trip.management_token != payload.management_token:
        raise HTTPException(status_code=403, detail="Invalid management token")
        
    if trip.status != TripStatus.survey:
        raise HTTPException(status_code=400, detail="Trip is not in survey phase")
        
    total_participants = db.query(Participant).filter(Participant.trip_id == trip.id).count()
    responded_participants = db.query(Participant).filter(Participant.trip_id == trip.id, Participant.responded).count()
    
    trip.status = TripStatus.reveal
    db.commit()

    # A/B prompt_version coin flip
    prompt_version = "v1" if random.random() > 0.5 else "v2"
    background_tasks.add_task(trigger_pipeline, trip.id, prompt_version)
    
    # Broadcast status update immediately on force close
    await broadcast_trip_status(trip.id, db)
    
    return ForceCloseResponse(
        ok=True,
        responses_received=responded_participants,
        total_participants=total_participants
    )


@router.get("/participants/validate/{token}", response_model=ParticipantValidateOut)
def validate_participant_token(token: UUID, db: Session = Depends(get_db)):
    """Validate a participant token and return their info + trip status."""
    participant = db.query(Participant).filter(Participant.unique_token == token).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    trip = db.query(Trip).filter(Trip.id == participant.trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return ParticipantValidateOut(
        participant_id=participant.id,
        participant_name=participant.name,
        trip_id=trip.id,
        trip_status=trip.status.value,
        responded=participant.responded,
        voted=participant.voted
    )


