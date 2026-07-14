from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel
import random

import logging
from packvote.backend.core.database import get_db, SessionLocal
from packvote.backend.models.db import Trip, Participant, TripStatus, Response as DBResponse, Recommendation
from packvote.shared.schemas import SurveySubmit, ForceCloseRequest, ForceCloseResponse
from packvote.backend.pipeline.graph import pipeline
from packvote.backend.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["responses"])

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
            
    except Exception as e:
        logger.error(f"Error running LangGraph pipeline for trip {trip_id}: {e}", exc_info=True)


@router.post("/responses", status_code=status.HTTP_200_OK)
def submit_response(
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

    return {"message": "Response recorded"}

class TripStatusOut(BaseModel):
    status: str

@router.get("/trips/{trip_id}/status", response_model=TripStatusOut)
def get_trip_status(trip_id: UUID, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return TripStatusOut(status=trip.status.value)

@router.post("/trips/{trip_id}/force-close", response_model=ForceCloseResponse)
def force_close_survey(
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
    
    return ForceCloseResponse(
        ok=True,
        responses_received=responded_participants,
        total_participants=total_participants
    )
