from typing import TypedDict

class TripState(TypedDict):
    trip_id: str
    prompt_version: str                  # "v1" or "v2"
    responses: list[dict]
    aggregated: dict
    retrieved_destinations: list[dict]   # populated by Node 2 RAG retrieval
    recommendations: list[dict]
    critic_score: float
    critic_feedback: str
    retry_count: int
