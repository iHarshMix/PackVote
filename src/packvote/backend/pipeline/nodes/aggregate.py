from statistics import median
from collections import Counter
from uuid import UUID
from packvote.backend.core.database import SessionLocal
from packvote.backend.models.db import Response, Destination
from packvote.backend.pipeline.state import TripState

def aggregate_node(state: TripState) -> TripState:
    # Safely convert trip_id to UUID object if it's passed as a string
    trip_id = state["trip_id"]
    if isinstance(trip_id, str):
        trip_id = UUID(trip_id)

    with SessionLocal() as db:
        # 1. Pull all responses for this trip
        responses = db.query(Response).filter_by(trip_id=trip_id).all()
        state["responses"] = [
            {"swipes": r.swipes, "budget_max": r.budget_max, "unavailable_dates": r.unavailable_dates}
            for r in responses
        ]

        # 2. Count swipe-rights per destination
        dest_counts = Counter()
        liked_names = []
        for r in responses:
            for swipe in r.swipes:
                if swipe.get("liked"):
                    dest_counts[swipe["destination"]] += 1
                    liked_names.append(swipe["destination"])
        top_destinations = [name for name, _ in dest_counts.most_common(5)]

        # 3. Compute median budget across all participants
        budgets = [r.budget_max for r in responses]
        budget_sweet_spot = int(median(budgets)) if budgets else 15000

        # 4. JOIN destinations table to look up vibe_tags for liked destinations
        dest_rows = db.query(Destination).filter(Destination.name.in_(set(liked_names))).all()
        all_vibes = []
        for d in dest_rows:
            all_vibes.extend(d.vibe_tags or [])
        vibe_overlap = [tag for tag, _ in Counter(all_vibes).most_common(3)]

        # 5. Union all unavailable dates
        all_conflicts = set()
        for r in responses:
            all_conflicts.update(r.unavailable_dates or [])

    state["aggregated"] = {
        "top_destinations": top_destinations,
        "budget_sweet_spot": budget_sweet_spot,
        "vibe_overlap": vibe_overlap,
        "date_conflicts": sorted(all_conflicts),
    }
    return state
