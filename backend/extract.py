import os
import json
import logging
from typing import List
from pydantic import ValidationError, BaseModel
from google import genai
from google.genai import types

from models import ExtractedReference

logger = logging.getLogger(__name__)

class ReferenceExtractionError(Exception):
    """Exception raised for errors during Gemini reference extraction."""
    pass

class ExtractionResponse(BaseModel):
    references: List[ExtractedReference]

PROMPT_TEMPLATE = """
Extract all bibliographic references from the following text.
Extract references only.
Do not verify whether references are real.
Do not search the internet.
Do not invent missing metadata.
Preserve missing values as null/empty values according to the schema.
Preserve the original reference text in `raw`.
Return structured JSON only, strictly matching this schema:
{{
  "references": [
    {{
      "raw": "exact original text",
      "authors": ["Author 1", "Author 2"],
      "title": "Title",
      "year": 2023,
      "venue": "Journal Name",
      "doi": "10.xxx/yyy",
      "type": "article|conference|book|web|other"
    }}
  ]
}}

Text to extract references from:
{text}
"""

def extract_references(text: str) -> List[ExtractedReference]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ReferenceExtractionError("GEMINI_API_KEY environment variable is not set")
        
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        raise ReferenceExtractionError(f"Failed to initialize Gemini client: {e}")
        
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    
    prompt = PROMPT_TEMPLATE.format(text=text)
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.0
    )
    
    attempts = 0
    max_attempts = 2
    
    while attempts < max_attempts:
        attempts += 1
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            data = json.loads(response_text)
            parsed = ExtractionResponse.model_validate(data)
            return parsed.references
            
        except json.JSONDecodeError as e:
            logger.warning(f"Attempt {attempts}: Failed to parse JSON from Gemini")
            if attempts >= max_attempts:
                raise ReferenceExtractionError(f"Failed to parse valid JSON from Gemini after retries")
            prompt = f"Previous response was not valid JSON. Please strictly output ONLY valid JSON matching the schema.\n\n{PROMPT_TEMPLATE.format(text=text)}"
            
        except ValidationError as e:
            logger.warning(f"Attempt {attempts}: Validation failed for extracted references: {e}")
            if attempts >= max_attempts:
                raise ReferenceExtractionError(f"Extracted references failed schema validation after retries: {e}")
            prompt = f"Previous response failed schema validation. Check enum types and missing fields. Please strictly follow the schema.\n\n{PROMPT_TEMPLATE.format(text=text)}"
            
        except Exception as e:
            # We don't indiscriminately retry all SDK/API exceptions
            raise ReferenceExtractionError(f"Gemini API request failed: {e}")
            
    raise ReferenceExtractionError("Extraction failed")
