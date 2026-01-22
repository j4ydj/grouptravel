"""SQLAlchemy 2.0 database models."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Enum as SQLEnum, Boolean, Float
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
    
    # Phase 2: Reproducibility fields
    pricing_provider = Column(String, nullable=True)  # "mock", "duffel", etc.
    pricing_cache_version = Column(String, nullable=True)
    random_seed = Column(Integer, nullable=True)
    config_snapshot = Column(JSON, nullable=True)  # Frozen settings at simulation time
    
    # Relationships
    event = relationship("Event", back_populates="simulation_results")


class Hotel(Base):
    """Hotel model."""
    __tablename__ = "hotels"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    airport_code = Column(String(3), nullable=False, index=True)
    chain = Column(String, nullable=True)
    approved = Column(Boolean, default=False, nullable=False)
    corporate_rate = Column(Float, nullable=True)
    distance_to_venue_km = Column(Float, nullable=True)
    capacity = Column(Integer, nullable=True)
    has_meeting_space = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transfer_options = relationship("TransferOption", back_populates="hotel", cascade="all, delete-orphan")


class TransferMode(str, enum.Enum):
    """Transfer mode enumeration."""
    UBER = "uber"
    VAN = "van"
    TRAIN = "train"
    BUS = "bus"


class TransferOption(Base):
    """Transfer option model."""
    __tablename__ = "transfer_options"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    airport_code = Column(String(3), nullable=False, index=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=True)
    mode = Column(SQLEnum(TransferMode), nullable=False)
    capacity = Column(Integer, nullable=False)
    cost_per_trip = Column(Float, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    hotel = relationship("Hotel", back_populates="transfer_options")


class PreferenceProfile(Base):
    """Preference profile model for learning attendee preferences."""
    __tablename__ = "preference_profiles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    attendee_id = Column(String, ForeignKey("attendees.id"), unique=True, nullable=False, index=True)
    prefers_early_flights = Column(Float, default=0.5, nullable=False)  # 0-1
    avoids_connections = Column(Float, default=0.5, nullable=False)     # 0-1
    preferred_hubs = Column(JSON, default=list)
    typical_arrival_window = Column(JSON, nullable=True)  # {start: "HH:MM", end: "HH:MM"}
    reliability_score = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attendee = relationship("Attendee", backref="preference_profile")


class AuditLog(Base):
    """Audit log model for tracking actions."""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String, ForeignKey("events.id"), nullable=True, index=True)
    user = Column(String, nullable=False)
    action = Column(String, nullable=False)  # simulate, export, whatif, etc.
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    before_hash = Column(String, nullable=True)
    after_hash = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)
