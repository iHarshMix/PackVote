import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from packvote.backend.core.database import Base
from packvote.backend.core.config import settings

def utcnow():
    return datetime.now(timezone.utc)

class TripStatus(str, enum.Enum):
    setup = "setup"
    survey = "survey"
    reveal = "reveal"
    voting = "voting"
    complete = "complete"

class Trip(Base):
    __tablename__ = "trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    organiser_email = Column(String, nullable=False)
    management_token = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    dates_rough = Column(String, nullable=False)
    status = Column(Enum(TripStatus), default=TripStatus.setup, nullable=False)
    vote_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    participants = relationship("Participant", back_populates="trip")
    responses = relationship("Response", back_populates="trip")
    recommendations = relationship("Recommendation", back_populates="trip")
    votes = relationship("Vote", back_populates="trip")

class Participant(Base):
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False)
    name = Column(String, nullable=False)
    unique_token = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    is_organiser = Column(Boolean, default=False, nullable=False)
    responded = Column(Boolean, default=False, nullable=False)
    voted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    trip = relationship("Trip", back_populates="participants")

class Response(Base):
    __tablename__ = "responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False)
    swipes = Column(JSONB, nullable=False)
    budget_max = Column(Integer, nullable=False)
    unavailable_dates = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    trip = relationship("Trip", back_populates="responses")

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False)
    destination = Column(String, nullable=False)
    fit_reason = Column(String, nullable=False)
    tradeoff = Column(String, nullable=False)
    budget_estimate = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False)
    prompt_version = Column(String, nullable=True)
    model_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    trip = relationship("Trip", back_populates="recommendations")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False)
    ranking = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    trip = relationship("Trip", back_populates="votes")

class Destination(Base):
    __tablename__ = "destinations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    vibe_tags = Column(ARRAY(String), nullable=False)
    budget_low = Column(Integer, nullable=False)
    budget_high = Column(Integer, nullable=False)
    best_months = Column(ARRAY(String), nullable=False)
    activities = Column(ARRAY(String), nullable=False)
    embedding = Column(Vector(settings.embedding_dimension), nullable=True)
