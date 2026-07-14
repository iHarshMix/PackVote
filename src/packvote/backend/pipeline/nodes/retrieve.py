from sqlalchemy import text
from packvote.backend.core.database import SessionLocal
from packvote.backend.core.llm import get_embeddings
from packvote.backend.pipeline.state import TripState

def retrieve_node(state: TripState) -> TripState:
    agg = state["aggregated"]

    # Build a natural language query from aggregated signals
    query = (
        f"{' '.join(agg['vibe_overlap'])} destination "
        f"budget {agg['budget_sweet_spot']} INR "
        f"avoid {' '.join(agg.get('date_conflicts', []))}"
    )

    # Standardized LangChain Embeddings interface
    embeddings = get_embeddings()
    query_embedding = embeddings.embed_query(query)

    # Cosine similarity search via pgvector using our own SessionLocal
    with SessionLocal() as db:
        results = db.execute(
            text("""
                SELECT name, vibe_tags, budget_low, budget_high, best_months, activities
                FROM destinations
                ORDER BY embedding <=> CAST(:emb AS vector)
                LIMIT 5
            """),
            {"emb": query_embedding}
        ).fetchall()


    state["retrieved_destinations"] = [dict(r._mapping) for r in results]
    return state
