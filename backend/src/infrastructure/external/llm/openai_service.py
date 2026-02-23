import json
from typing import Dict, Any, Optional
from openai import OpenAI

from .base import LLMService, LLMExtractionResult


class OpenAIService(LLMService):
    """OpenAI LLM implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def extract_fields(self, text: str, document_type: str, schema: Dict[str, Any],
                       layout_context: Optional[str] = None) -> LLMExtractionResult:
        """Extract structured fields using OpenAI"""
        prompt = self._build_prompt(text, document_type, schema, layout_context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured data from logistics documents."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty response from OpenAI")
            
            result_json = json.loads(response.choices[0].message.content)
            
            # Extract structured data and confidence scores
            structured_data = result_json.get("data", {})
            confidence_scores = result_json.get("confidence", {})
            
            metadata = {
                "model": self.model,
                "provider": "openai",
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
            return LLMExtractionResult(
                structured_data=structured_data,
                confidence_scores=confidence_scores,
                metadata=metadata
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response from OpenAI: {e}")
        except Exception as e:
            raise ValueError(f"OpenAI API error: {str(e)}")
    
    def _build_prompt(self, text: str, document_type: str, schema: Dict[str, Any],
                      layout_context: Optional[str] = None) -> str:
        """Build extraction prompt"""
        schema_str = json.dumps(schema, indent=2)

        if layout_context:
            document_section = f"""Document (layout-aware):
{layout_context}"""
            layout_hint = "\nKey-value pairs like 'Field: Value' directly map to fields. Table rows map to line-item arrays."
        else:
            document_section = f"""Document Text:
{text[:4000]}"""
            layout_hint = ""

        return f"""Extract structured data from the following {document_type} document text.

{document_section}

Expected Schema:
{schema_str}

Return a JSON object with:
- "data": Object containing extracted fields matching the schema
- "confidence": Object with confidence scores (0.0-1.0) for each field

For missing fields, use null. For confidence, estimate based on clarity of the information in the text.{layout_hint}"""

