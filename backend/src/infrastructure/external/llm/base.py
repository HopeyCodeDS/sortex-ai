from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class LLMExtractionResult:
    """LLM extraction result"""
    
    def __init__(self, structured_data: Dict[str, Any], confidence_scores: Dict[str, float], metadata: Dict[str, Any] = None):
        self.structured_data = structured_data
        self.confidence_scores = confidence_scores
        self.metadata = metadata or {}


class LLMService(ABC):
    """Abstract LLM service interface"""
    
    @abstractmethod
    def extract_fields(self, text: str, document_type: str, schema: Dict[str, Any],
                       layout_context: Optional[str] = None) -> LLMExtractionResult:
        """
        Extract structured fields from text using LLM.

        Args:
            text: Extracted text from OCR
            document_type: Type of document (CMR, INVOICE, etc.)
            schema: JSON schema defining expected fields
            layout_context: Spatially-reconstructed text from LayoutAnalyzer (optional)

        Returns:
            LLMExtractionResult with structured data and confidence scores
        """
        pass

