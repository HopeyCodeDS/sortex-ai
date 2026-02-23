from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel

from ...domain.entities.extraction import Extraction, ExtractionMethod


class ExtractionDTO(BaseModel):
    id: UUID
    document_id: UUID
    extraction_method: ExtractionMethod
    raw_text: Optional[str]
    structured_data: Dict[str, Any]
    confidence_scores: Dict[str, Any]
    extracted_at: datetime
    extraction_metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True

    @classmethod
    def from_entity(cls, entity: Extraction) -> "ExtractionDTO":
        return cls(
            id=entity.id,
            document_id=entity.document_id,
            extraction_method=entity.extraction_method,
            raw_text=entity.raw_text,
            structured_data=entity.structured_data,
            confidence_scores=entity.confidence_scores,
            extracted_at=entity.extracted_at,
            extraction_metadata=entity.extraction_metadata,
        )

