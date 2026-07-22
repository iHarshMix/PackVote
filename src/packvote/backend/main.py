from fastapi import FastAPI
from packvote.backend.routers import trips, responses, recovery, websockets, votes, results
from packvote.backend.core.database import Base, engine
# We must import our db models so that SQLAlchemy knows about them
# when calling Base.metadata.create_all

from sqlalchemy import text

# Automatically create the vector extension and database tables when the application starts
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PackVote API")

app.include_router(trips.router)
app.include_router(responses.router)
app.include_router(recovery.router)
app.include_router(websockets.router)
app.include_router(votes.router)
app.include_router(results.router)

@app.on_event("startup")
def auto_seed():
    from packvote.backend.core.database import SessionLocal
    from packvote.backend.models.db import Destination
    db = SessionLocal()
    try:
        if db.query(Destination).count() == 0:
            print("Destination table empty. Triggering automatic database seeding...")
            try:
                from scripts.seed_destinations import main as seed_main
                seed_main()
            except Exception as e:
                print(f"Auto-seeding error: {e}")
    except Exception as e:
        print(f"Database startup check warning: {e}")
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {"status": "ok"}
