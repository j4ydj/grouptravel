"""SQLAlchemy 2.0 database models."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum
import uuid


Base = declarative_base()


class TravelClass(str, enum.Enum):
    """Travel class enumeration."""
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class Attendee(Base):
    """Attendee model."""
    __tablename__ = "attendees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, unique=True, nullable=False, index=True)
    home_airport = Column(String(3), nullable=False)  # IATA code
    preferred_airports = Column(JSON, default=list)
    travel_class = Column(SQLEnum(TravelClass), default=TravelClass.ECONOMY)
    preferred_airlines = Column(JSON, default=list)
    time_constraints = Column(JSON, default=dict)
    timezone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event_attendees = relationship("EventAttendee", back_populates="attendee", cascade="all, delete-orphan")


class Event(Base):
    """Event model."""
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    candidate_locations = Column(JSON, nullable=False)  # List of IATA codes
    candidate_date_windows = Column(JSON, nullable=False)  # List of {start_date, end_date}
    duration_days = Column(Integer, nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event_attendees = relationship("EventAttendee", back_populates="event", cascade="all, delete-orphan")
    simulation_results = relationship("SimulationResult", back_populates="event", cascade="all, delete-orphan")


class EventAttendee(Base):
    """Many-to-many join table for events and attendees."""
    __tablename__ = "event_attendees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String, ForeignKey("events.id"), nullable=False, index=True)
    attendee_id = Column(String, ForeignKey("attendees.id"), nullable=False, index=True)
    
    # Relationships
    event = relationship("Event", back_populates="event_attendees")
    attendee = relationship("Attendee", back_populates="event_attendees")


class SimulationResult(Base):
    """Simulation result model."""
    __tablename__ = "simulation_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String, ForeignKey("events.id"), nullable=False, index=True)
    results = Column(JSON, nullable=False)  # Full simulation results JSON
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event = relationship("Event", back_populates="simulation_results")
