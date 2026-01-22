"""PII redaction service."""
import re
from typing import List


class RedactionService:
    """Service for redacting PII from text."""
    
    # Common email pattern
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )
    
    # Common name patterns (simple heuristic - can be improved)
    # This is a basic pattern - in production, use more sophisticated NLP
    NAME_PATTERNS = [
        re.compile(r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b'),
        re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'),  # First Last
    ]
    
    def redact_email(self, text: str) -> str:
        """Redact email addresses."""
        return self.EMAIL_PATTERN.sub('[EMAIL_REDACTED]', text)
    
    def redact_names(self, text: str) -> str:
        """Redact potential names (basic heuristic)."""
        result = text
        for pattern in self.NAME_PATTERNS:
            result = pattern.sub('[NAME_REDACTED]', result)
        return result
    
    def redact_text(self, text: str) -> str:
        """Redact all PII from text."""
        if not isinstance(text, str):
            return text
        
        result = self.redact_email(text)
        result = self.redact_names(result)
        return result
    
    def redact_list(self, items: List[str]) -> List[str]:
        """Redact PII from a list of strings."""
        return [self.redact_text(item) for item in items]
