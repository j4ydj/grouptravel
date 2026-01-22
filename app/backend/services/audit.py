"""Audit logging service."""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import hashlib
import json
from app.backend.db.models import AuditLog
from app.backend.core.config import settings
from app.backend.core.security import get_current_user


class AuditService:
    """Service for audit logging."""
    
    def log_action(
        self,
        action: str,
        event_id: Optional[str],
        user: Optional[str],
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Optional[AuditLog]:
        """
        Log an action to audit log.
        
        Args:
            action: Action name (simulate, export, whatif, etc.)
            event_id: Event ID (if applicable)
            user: User identifier
            before_state: State before action (optional)
            after_state: State after action (optional)
            metadata: Additional metadata (optional)
            db: Database session
        
        Returns:
            AuditLog entry or None if db not provided
        """
        if not db:
            return None
        
        # Compute hashes
        before_hash = None
        if before_state:
            before_hash = hashlib.sha256(
                json.dumps(before_state, sort_keys=True).encode()
            ).hexdigest()[:16]
        
        after_hash = None
        if after_state:
            after_hash = hashlib.sha256(
                json.dumps(after_state, sort_keys=True).encode()
            ).hexdigest()[:16]
        
        # Get user if not provided
        if not user:
            user = get_current_user() or "system"
        
        audit_entry = AuditLog(
            event_id=event_id,
            user=user,
            action=action,
            before_hash=before_hash,
            after_hash=after_hash,
            metadata_json=metadata or {}
        )
        
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        
        return audit_entry
    
    def get_reproducibility_snapshot(
        self,
        pricing_provider: str,
        pricing_cache_version: Optional[str] = None,
        random_seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create reproducibility snapshot.
        
        Args:
            pricing_provider: Pricing provider name
            pricing_cache_version: Cache version (optional)
            random_seed: Random seed (optional)
        
        Returns:
            Snapshot dict
        """
        return {
            "pricing_provider": pricing_provider,
            "pricing_cache_version": pricing_cache_version,
            "random_seed": random_seed,
            "config": {
                "price_volatility": settings.price_volatility,
                "llm_provider": settings.llm_provider
            },
            "timestamp": datetime.utcnow().isoformat()
        }
