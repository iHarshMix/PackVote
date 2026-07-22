import json
from packvote.backend.core.database import SessionLocal, engine, Base
from packvote.backend.models.db import Destination
from packvote.backend.core.config import settings


from sqlalchemy import text

def main():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    import os
    candidate_paths = [
        "seeds/destinations.json",
        "/app/seeds/destinations.json",
        os.path.join(os.path.dirname(__file__), "../seeds/destinations.json"),
    ]
    data = None
    for p in candidate_paths:
        if os.path.exists(p):
            with open(p, "r") as f:
                data = json.load(f)
            break
    if data is None:
        raise FileNotFoundError("Could not locate seeds/destinations.json")

    db = SessionLocal()
    try:
        # Clear existing destinations
        db.query(Destination).delete()

        # Try to initialise the embeddings model via the provider-agnostic factory
        embeddings_model = None
        try:
            from packvote.backend.core.llm import get_embeddings
            embeddings_model = get_embeddings()
            # Quick sanity check — will raise if the API key is missing/invalid
            _ = embeddings_model.embed_query("test")
            print(f"Using {settings.embedding_provider}/{settings.embedding_model} for embeddings.")
        except Exception as e:
            print(f"Warning: Could not initialise embedding provider "
                  f"({settings.embedding_provider}/{settings.embedding_model}): {e}")
            print(f"Falling back to mocked [0.0]*{settings.embedding_dimension} embeddings.")
            embeddings_model = None

        for d in data:
            embedding = [0.0] * settings.embedding_dimension
            if embeddings_model:
                profile_text = (
                    f"{d['name']} | Vibes: {', '.join(d['vibe_tags'])} | "
                    f"Activities: {', '.join(d['activities'])} | "
                    f"Best months: {', '.join(d['best_months'])}"
                )
                embedding = embeddings_model.embed_query(profile_text)

            dest = Destination(
                name=d["name"],
                vibe_tags=d["vibe_tags"],
                budget_low=d["budget_low"],
                budget_high=d["budget_high"],
                best_months=d["best_months"],
                activities=d["activities"],
                embedding=embedding,
            )
            db.add(dest)

        db.commit()
        print(f"Successfully seeded {len(data)} destinations.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
