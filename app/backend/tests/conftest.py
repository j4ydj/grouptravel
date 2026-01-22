"""Pytest configuration and fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.backend.db.models import Base
from app.backend.db.session import get_db
from app.backend.main import app
from fastapi.testclient import TestClient
import tempfile
import os


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    # Create temporary SQLite database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        os.unlink(db_path)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_attendee_data():
    """Sample attendee data for testing."""
    return {
        "employee_id": "EMP001",
        "home_airport": "JFK",
        "travel_class": "economy",
        "preferred_airports": [],
        "preferred_airlines": [],
        "time_constraints": {},
        "timezone": "America/New_York"
    }


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "name": "Test Workshop",
        "candidate_locations": ["LIS", "MUC"],
        "candidate_date_windows": [
            {
                "start_date": "2024-06-01",
                "end_date": "2024-06-08"
            }
        ],
        "duration_days": 3,
        "created_by": "test_user"
    }
