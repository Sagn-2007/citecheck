import re
from rapidfuzz import fuzz
from typing import Optional, List, Tuple
from models import (
    ExtractedReference,
    ScholarlyCandidate,
    ReferenceResult,
    Verdict,
    FieldDifference,
    ReferenceType
)

THRESHOLD_VERIFIED = 90
THRESHOLD_NOT_FOUND = 70

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\\[a-zA-Z]+(\s|{.*?})', ' ', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def compare_titles(submitted: str, matched: str) -> float:
    s_norm = normalize_text(submitted)
    m_norm = normalize_text(matched)
    if not s_norm or not m_norm:
        return 0.0
    
    score_token_set = fuzz.token_set_ratio(s_norm, m_norm)
    score_ratio = fuzz.ratio(s_norm, m_norm)
    return max(score_token_set, score_ratio)

def extract_surname(author: str) -> str:
    author = author.split(',')[0] if ',' in author else author.split(' ')[-1]
    return normalize_text(author)

def compare_authors(submitted: List[str], matched: List[str]) -> Tuple[bool, float]:
    if not submitted or not matched:
        return False, 0.0
    
    sub_sub = submitted[:3]
    mat_sub = matched[:3]
    
    sub_surnames = {extract_surname(a) for a in sub_sub}
    mat_surnames = {extract_surname(a) for a in mat_sub}
    
    overlap = len(sub_surnames.intersection(mat_surnames))
    overlap_score = (overlap / max(len(sub_surnames), 1)) * 100
    
    first_sub = extract_surname(submitted[0])
    first_mat = extract_surname(matched[0])
    
    first_author_ok = first_sub in mat_surnames or first_mat in sub_surnames
    
    return first_author_ok, overlap_score

def compare_years(submitted: Optional[int], matched: Optional[int]) -> bool:
    if submitted is None or matched is None:
        return True
    return abs(submitted - matched) <= 1

def compare_venues(submitted: Optional[str], matched: Optional[str]) -> float:
    if not submitted or not matched:
        return 100.0
    s_norm = normalize_text(submitted)
    m_norm = normalize_text(matched)
    return fuzz.token_set_ratio(s_norm, m_norm)

def generate_field_differences(sub: ExtractedReference, mat: ScholarlyCandidate) -> List[FieldDifference]:
    diffs = []
    
    if sub.title and mat.title:
        title_sim = compare_titles(sub.title, mat.title)
        if title_sim < THRESHOLD_VERIFIED:
            diffs.append(FieldDifference(field_name="title", submitted=sub.title, matched=mat.title))
            
    if sub.year is not None and mat.year is not None and not compare_years(sub.year, mat.year):
        diffs.append(FieldDifference(field_name="year", submitted=sub.year, matched=mat.year))
        
    first_author_ok, overlap = compare_authors(sub.authors, mat.authors)
    if not first_author_ok or overlap < 100:
        diffs.append(FieldDifference(field_name="authors", submitted=", ".join(sub.authors), matched=", ".join(mat.authors)))
        
    if sub.venue and mat.venue:
        venue_sim = compare_venues(sub.venue, mat.venue)
        if venue_sim < 70:
            diffs.append(FieldDifference(field_name="venue", submitted=sub.venue, matched=mat.venue))
            
    if sub.doi and mat.doi and normalize_text(sub.doi) != normalize_text(mat.doi):
        diffs.append(FieldDifference(field_name="doi", submitted=sub.doi, matched=mat.doi))
        
    return diffs

def assign_verdict(
    ref_type: ReferenceType,
    title_sim: float, 
    first_author_ok: bool, 
    year_ok: bool, 
    doi_status: str, 
    found: bool
) -> Verdict:
    if doi_status == "invalid":
        return Verdict.DOI_INVALID
        
    if not found or title_sim < THRESHOLD_NOT_FOUND:
        if ref_type in (ReferenceType.BOOK, ReferenceType.WEB, ReferenceType.OTHER):
            return Verdict.CANNOT_VERIFY
        return Verdict.NOT_FOUND

    if title_sim >= THRESHOLD_VERIFIED and first_author_ok and year_ok:
        return Verdict.VERIFIED
        
    return Verdict.MISMATCH

def compare_reference(
    extracted: ExtractedReference, 
    candidate: Optional[ScholarlyCandidate], 
    doi_status: str = "valid"
) -> ReferenceResult:
    
    if not candidate:
        verdict = assign_verdict(extracted.type, 0.0, False, False, doi_status, False)
        return ReferenceResult(
            extracted_reference=extracted,
            verdict=verdict,
            closest_candidate=None,
            similarity=0.0,
            field_differences=[]
        )
        
    title_sim = compare_titles(extracted.title, candidate.title)
    first_author_ok, _ = compare_authors(extracted.authors, candidate.authors)
    year_ok = compare_years(extracted.year, candidate.year)
    
    verdict = assign_verdict(
        ref_type=extracted.type,
        title_sim=title_sim,
        first_author_ok=first_author_ok,
        year_ok=year_ok,
        doi_status=doi_status,
        found=True
    )
    
    diffs = generate_field_differences(extracted, candidate)
    
    return ReferenceResult(
        extracted_reference=extracted,
        verdict=verdict,
        closest_candidate=candidate,
        similarity=title_sim,
        field_differences=diffs
    )
