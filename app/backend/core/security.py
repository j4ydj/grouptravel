"""Security utilities (placeholder for MVP)."""
from typing import Optional


def get_current_user() -> Optional[str]:
    """
    Get current authenticated user.
    
    For MVP, returns a placeholder. In production, this would
    extract user from JWT token or session.
    """
    # TODO: Implement actual authentication
    return "system"
