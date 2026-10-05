from typing import Optional, List
from models import ExtractedReference, ReferenceResult, ScholarlyCandidate
from match import compare_titles, compare_authors, compare_years, compare_reference
from lookup import lookup_by_doi, search_by_bibliographic, search_openalex, search_semantic_scholar

def _score_candidate(ref: ExtractedReference, cand: ScholarlyCandidate) -> float:
    # Use existing matching signals to score the candidate.
    title_sim = compare_titles(ref.title, cand.title)
    first_author_ok, author_overlap = compare_authors(ref.authors, cand.authors)
    year_ok = compare_years(ref.year, cand.year)
    
    # Deterministic scoring: Title is the most important signal (0-100)
    score = title_sim
    
    # Bonuses for matching other vital fields
    if first_author_ok:
        score += 15.0
    
    # Partial bonus for author overlap
    score += (author_overlap * 0.1) # Max 10.0 bonus
    
    if year_ok:
        score += 10.0
        
    return score

def _select_best_candidate(ref: ExtractedReference, candidates: List[ScholarlyCandidate]) -> Optional[ScholarlyCandidate]:
    if not candidates:
        return None
        
    best_cand = None
    best_score = -1.0
    
    for cand in candidates:
        score = _score_candidate(ref, cand)
        if score > best_score:
            best_score = score
            best_cand = cand
            
    return best_cand

async def verify_reference(ref: ExtractedReference) -> ReferenceResult:
    doi_status = "valid"
    candidate = None
    
    if ref.doi:
        candidate = await lookup_by_doi(ref.doi)
        if not candidate:
            doi_status = "invalid"
    else:
        first_author = ref.authors[0] if ref.authors else ""
        
        # 1. Crossref
        crossref_candidates = await search_by_bibliographic(ref.title, first_author)
        candidate = _select_best_candidate(ref, crossref_candidates)
        
        # 2. OpenAlex (if Crossref is weak/empty)
        if not candidate or _score_candidate(ref, candidate) < 90.0:
            openalex_candidates = await search_openalex(ref.title)
            
            # Re-evaluate all candidates to find the absolute strongest
            candidate = _select_best_candidate(ref, crossref_candidates + openalex_candidates)
            
            # 3. Semantic Scholar (if Crossref + OpenAlex is weak/empty)
            if not candidate or _score_candidate(ref, candidate) < 90.0:
                s2_candidates = await search_semantic_scholar(ref.title)
                
                # Re-evaluate all candidates from all three sources
                candidate = _select_best_candidate(ref, crossref_candidates + openalex_candidates + s2_candidates)
            
    # Delegate final decision and field differences generation entirely to match.py
    return compare_reference(ref, candidate, doi_status=doi_status)
