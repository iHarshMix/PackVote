from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from collections import Counter
from statistics import median
from datetime import datetime, timezone
import logging

from packvote.backend.core.database import get_db
from packvote.backend.models.db import (
    Trip, Participant, TripStatus,
    Response as DBResponse, Recommendation, Vote, Destination,
)
from packvote.shared.schemas import RevealOut, ResultOut, RecommendationOut
from packvote.backend.core.tally import ranked_choice_tally

logger = logging.getLogger(__name__)

router = APIRouter(tags=["results"])


# ── Reveal endpoint ──────────────────────────────────────────────────────────

@router.get("/trips/{trip_id}/reveal", response_model=RevealOut)
def get_reveal(trip_id: UUID, db: Session = Depends(get_db)):
    """Return aggregated group preferences + AI recommendations."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.status not in (TripStatus.reveal, TripStatus.voting, TripStatus.complete):
        raise HTTPException(status_code=409, detail="Reveal data is not available yet")

    # ── Aggregate preferences from responses ─────────────────────────────
    responses = db.query(DBResponse).filter(DBResponse.trip_id == trip_id).all()
    participants = db.query(Participant).filter(Participant.trip_id == trip_id).all()

    # Swipe-right counts
    dest_counts: Counter = Counter()
    liked_names: list[str] = []
    for r in responses:
        for swipe in (r.swipes or []):
            if swipe.get("liked"):
                dest_counts[swipe["destination"]] += 1
                liked_names.append(swipe["destination"])
    top_destinations = [name for name, _ in dest_counts.most_common(5)]

    # Budget distribution — per participant for the bar chart
    budget_distribution = []
    for r in responses:
        # Find the participant name
        p = next((p for p in participants if p.id == r.participant_id), None)
        budget_distribution.append({
            "name": p.name if p else "Unknown",
            "budget_max": r.budget_max,
        })

    budget_sweet_spot = int(median([r.budget_max for r in responses])) if responses else 15000

    # Shared vibe tags — look up destinations table
    dest_rows = db.query(Destination).filter(Destination.name.in_(set(liked_names))).all()
    all_vibes: list[str] = []
    for d in dest_rows:
        all_vibes.extend(d.vibe_tags or [])
    vibe_overlap = [tag for tag, _ in Counter(all_vibes).most_common(3)]

    # Date conflicts
    all_conflicts: set[str] = set()
    for r in responses:
        all_conflicts.update(r.unavailable_dates or [])

    aggregated = {
        "top_destinations": top_destinations,
        "budget_sweet_spot": budget_sweet_spot,
        "budget_distribution": budget_distribution,
        "vibe_overlap": vibe_overlap,
        "date_conflicts": sorted(all_conflicts),
    }

    # ── Fetch recommendations ────────────────────────────────────────────
    recs = db.query(Recommendation).filter(
        Recommendation.trip_id == trip_id
    ).order_by(Recommendation.rank).all()

    recommendations = [
        RecommendationOut(
            destination=r.destination,
            fit_reason=r.fit_reason,
            tradeoff=r.tradeoff,
            budget_estimate=r.budget_estimate,
        )
        for r in recs
    ]

    return RevealOut(aggregated=aggregated, recommendations=recommendations)


# ── Result endpoint ──────────────────────────────────────────────────────────

@router.get("/trips/{trip_id}/result", response_model=ResultOut)
def get_result(trip_id: UUID, db: Session = Depends(get_db)):
    """Return the winner, vote breakdown, and AI summary."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.status not in (TripStatus.voting, TripStatus.complete):
        raise HTTPException(status_code=409, detail="Results are not available yet")

    # If already computed, return cached results
    if trip.status == TripStatus.complete and trip.winner:
        return ResultOut(
            winner=trip.winner,
            vote_breakdown=trip.vote_breakdown or {},
            ai_summary=trip.ai_summary or "",
        )

    # Check if voting is finished (all voted or deadline expired)
    total_participants = db.query(Participant).filter(
        Participant.trip_id == trip_id
    ).count()
    voted_count = db.query(Participant).filter(
        Participant.trip_id == trip_id,
        Participant.voted == True,
    ).count()

    all_voted = voted_count >= total_participants
    timer_expired = (
        trip.vote_deadline is not None
        and datetime.now(timezone.utc) >= trip.vote_deadline.replace(tzinfo=timezone.utc)
    )

    if not all_voted and not timer_expired:
        raise HTTPException(
            status_code=400,
            detail=f"Voting is still active ({voted_count}/{total_participants} voted)"
        )

    # ── Tally the votes ──────────────────────────────────────────────────
    votes = db.query(Vote).filter(Vote.trip_id == trip_id).all()
    ballots = [v.ranking for v in votes]

    if not ballots:
        raise HTTPException(status_code=400, detail="No votes were cast")

    # Build tiebreak data from recommendations
    recs = db.query(Recommendation).filter(
        Recommendation.trip_id == trip_id
    ).all()
    budget_estimates = {r.destination: r.budget_estimate for r in recs}

    # Swipe counts for tiebreak
    responses = db.query(DBResponse).filter(DBResponse.trip_id == trip_id).all()
    swipe_counts: Counter = Counter()
    for r in responses:
        for swipe in (r.swipes or []):
            if swipe.get("liked"):
                swipe_counts[swipe["destination"]] += 1

    winner, vote_breakdown = ranked_choice_tally(
        ballots=ballots,
        budget_estimates=budget_estimates,
        swipe_counts=dict(swipe_counts),
    )

    # ── Generate AI summary ──────────────────────────────────────────────
    ai_summary = _generate_ai_summary(winner, vote_breakdown, budget_estimates)

    # ── Cache results and transition to complete ─────────────────────────
    trip.winner = winner
    trip.vote_breakdown = vote_breakdown
    trip.ai_summary = ai_summary
    trip.status = TripStatus.complete
    db.commit()

    logger.info(f"Trip {trip_id}: winner is '{winner}', status → complete")

    return ResultOut(
        winner=winner,
        vote_breakdown=vote_breakdown,
        ai_summary=ai_summary,
    )


def _generate_ai_summary(winner: str, vote_breakdown: dict, budget_estimates: dict) -> str:
    """Generate a one-line AI summary of why the winner won."""
    try:
        from packvote.backend.core.llm import get_llm

        llm = get_llm()
        prompt = (
            f"In one concise sentence, explain why '{winner}' won a ranked-choice travel vote. "
            f"Vote breakdown: {vote_breakdown}. "
            f"Budget estimates: {budget_estimates}. "
            f"Keep it casual and fun — this is for a group chat."
        )
        result = llm.invoke(prompt)
        return result.content.strip()
    except Exception as e:
        logger.error(f"AI summary generation failed: {e}", exc_info=True)
        return f"{winner} won with the most votes — the group has spoken!"
