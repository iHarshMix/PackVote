from fastapi import FastAPI
from packvote.backend.routers import trips
from packvote.backend.core.database import Base, engine

app = FastAPI(title="PackVote API")

app.include_router(trips.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
