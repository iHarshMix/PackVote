from fastapi import FastAPI
from packvote.backend.routers import trips
from packvote.backend.core.database import Base, engine
# We must import our db models so that SQLAlchemy knows about them
# when calling Base.metadata.create_all
from packvote.backend.models import db

# Automatically create database tables when the application starts
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PackVote API")

app.include_router(trips.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
