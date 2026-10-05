from enum import Enum
from typing import List, Optional, Dict, Union
from pydantic import BaseModel

class ReferenceType(str, Enum):
    ARTICLE = "article"
    CONFERENCE = "conference"
    BOOK = "book"
    WEB = "web"
    OTHER = "other"

class ExtractedReference(BaseModel):
    raw: str
    authors: List[str]
    title: str
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    type: ReferenceType

class ScholarlyCandidate(BaseModel):
    title: str
    authors: List[str]
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    source: str
    url: Optional[str] = None

class Verdict(str, Enum):
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH"
    NOT_FOUND = "NOT_FOUND"
    DOI_INVALID = "DOI_INVALID"
    CANNOT_VERIFY = "CANNOT_VERIFY"

class FieldDifference(BaseModel):
    field_name: str
    submitted: Optional[Union[str, int]] = None
    matched: Optional[Union[str, int]] = None

class ReferenceResult(BaseModel):
    extracted_reference: ExtractedReference
    verdict: Verdict
    closest_candidate: Optional[ScholarlyCandidate] = None
    similarity: Optional[float] = None
    field_differences: Optional[List[FieldDifference]] = None

class VerifyResponse(BaseModel):
    results: List[ReferenceResult]
    total_references: int
    verdict_counts: Dict[Verdict, int]
    reliability_score: Optional[float] = None
from pydantic import BaseModel, model_validator

class VerifyRequest(BaseModel):
    references: Optional[List[ExtractedReference]] = None
    text: Optional[str] = None
    
    @model_validator(mode='after')
    def check_exactly_one_input(self) -> 'VerifyRequest':
        has_refs = self.references is not None
        has_text = self.text is not None
        
        if has_refs and has_text:
            raise ValueError("Provide either 'references' or 'text', not both.")
        if not has_refs and not has_text:
            raise ValueError("Provide either 'references' or 'text'.")
            
        if has_text:
            if not self.text.strip():
                raise ValueError("The 'text' field cannot be empty or whitespace-only.")
                
        return self
