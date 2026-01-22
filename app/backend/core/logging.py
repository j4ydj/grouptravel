"""Structured logging configuration with PII redaction."""
import logging
import sys
from typing import Any
from app.backend.services.redaction import RedactionService


class RedactionFilter(logging.Filter):
    """Log filter that redacts PII from log messages."""
    
    def __init__(self):
        super().__init__()
        self.redaction_service = RedactionService()
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Redact PII from log record."""
        if hasattr(record, "msg") and record.msg:
            record.msg = self.redaction_service.redact_text(str(record.msg))
        if hasattr(record, "args") and record.args:
            record.args = tuple(
                self.redaction_service.redact_text(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Add redaction filter to all handlers
    redaction_filter = RedactionFilter()
    for handler in logging.root.handlers:
        handler.addFilter(redaction_filter)
