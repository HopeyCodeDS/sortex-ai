from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class ExtractionMethod(str, Enum):
    OCR_ONLY = "OCR_ONLY"
    OCR_LLM = "OCR_LLM"
    MANUAL = "MANUAL"


class Extraction:
    """Extraction entity"""
    
    def __init__(
        self,
        id: UUID,
        document_id: UUID,
        extraction_method: ExtractionMethod,
        structured_data: Dict[str, Any],
        raw_text: Optional[str] = None,
        confidence_scores: Optional[Dict[str, Any]] = None,
        extraction_metadata: Optional[Dict[str, Any]] = None,
        extracted_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.document_id = document_id
        self.extraction_method = extraction_method
        self.raw_text = raw_text
        self.structured_data = structured_data
        self.confidence_scores = confidence_scores or {}
        self.extraction_metadata = extraction_metadata or {}
        self.extracted_at = extracted_at or datetime.utcnow()
        self.created_at = created_at or datetime.utcnow()
    
    def get_field_confidence(self, field_name: str) -> float:
        """Get confidence score for a specific field"""
        val = self.confidence_scores.get(field_name, 0.0)
        if isinstance(val, (int, float)):
            return float(val)
        return 0.0

    def get_average_confidence(self) -> float:
        """Get average confidence score across all fields"""
        if not self.confidence_scores:
            return 0.0
        scores = [
            float(v) for v in self.confidence_scores.values()
            if isinstance(v, (int, float))
        ]
        return sum(scores) / len(scores) if scores else 0.0

