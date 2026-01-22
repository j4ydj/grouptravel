"""Initialize database tables."""
from app.backend.db.session import engine
from app.backend.db.models import Base
from app.backend.services.pricing import Base as PricingBase


def init_db() -> None:
    """Create all database tables."""
    # Create main tables
    Base.metadata.create_all(bind=engine)
    
    # Create pricing cache table (uses same engine/database)
    PricingBase.metadata.create_all(bind=engine)
    
    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
