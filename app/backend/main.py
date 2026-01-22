"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.backend.core.config import settings
from app.backend.core.logging import setup_logging
from app.backend.db.init_db import init_db
from app.backend.api import attendees, events, ai, hotels, transfers, exports, whatif


# Setup logging
setup_logging(settings.log_level)

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="Group Travel Optimiser API",
    description="Internal tool for comparing workshop locations and dates",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For MVP, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(attendees.router, prefix="/api", tags=["attendees"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(ai.router, prefix="/api", tags=["ai"])
app.include_router(hotels.router, prefix="/api", tags=["hotels"])
app.include_router(transfers.router, prefix="/api", tags=["transfers"])
app.include_router(exports.router, prefix="/api", tags=["exports"])
app.include_router(whatif.router, prefix="/api", tags=["whatif"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Group Travel Optimiser API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
