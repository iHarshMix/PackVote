from fastapi import FastAPI
from packvote.backend.routers import trips, responses, recovery, websockets
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
@app.get("/health")
def health_check():
    return {"status": "ok"}
