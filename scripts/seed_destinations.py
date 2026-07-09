import json
import os
from openai import OpenAI
from packvote.backend.core.database import SessionLocal, engine, Base
from packvote.backend.models.db import Destination
from packvote.backend.core.config import settings

def main():
    Base.metadata.create_all(bind=engine)
    
    with open("seeds/destinations.json", "r") as f:
        data = json.load(f)
        
    db = SessionLocal()
    try:
        # Clear existing destinations
        db.query(Destination).delete()
        
        client = None
        if settings.openai_api_key and settings.openai_api_key != "sk-...":
            client = OpenAI(api_key=settings.openai_api_key)
        else:
            print("Warning: OPENAI_API_KEY is not set or is placeholder. Using mocked [0.0]*1536 embeddings.")
            
        for d in data:
            embedding = [0.0] * 1536
            if client:
                profile_text = f"{d['name']} | Vibes: {', '.join(d['vibe_tags'])} | Activities: {', '.join(d['activities'])} | Best months: {', '.join(d['best_months'])}"
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=profile_text
                )
                embedding = response.data[0].embedding
                
            dest = Destination(
                name=d["name"],
                vibe_tags=d["vibe_tags"],
                budget_low=d["budget_low"],
                budget_high=d["budget_high"],
                best_months=d["best_months"],
                activities=d["activities"],
                embedding=embedding
            )
            db.add(dest)
            
        db.commit()
        print(f"Successfully seeded {len(data)} destinations.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
