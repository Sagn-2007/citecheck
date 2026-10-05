import os
import re
import logging
import httpx
from typing import List, Optional, Dict, Any
from models import ScholarlyCandidate
from cache import generate_key, get_cached_candidates, set_cached_candidates

logger = logging.getLogger(__name__)

CROSSREF_API_URL = "https://api.crossref.org/works"
OPENALEX_API_URL = "https://api.openalex.org/works"
S2_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

def normalize_doi(doi: str) -> str:
    doi = doi.strip()
    doi = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi, flags=re.IGNORECASE)
    doi = re.sub(r'^doi:', '', doi, flags=re.IGNORECASE)
    return doi

def _map_crossref_item(item: Dict[str, Any]) -> ScholarlyCandidate:
    title = ""
    if "title" in item and item["title"]:
        title = item["title"][0]
        
    authors = []
    for a in item.get("author", []):
        given = a.get("given", "")
        family = a.get("family", "")
        if family:
            author_str = f"{family}, {given}".strip(', ')
            authors.append(author_str)
            
    year = None
    pub_date = item.get("published") or item.get("published-print") or item.get("published-online")
    if pub_date and "date-parts" in pub_date and pub_date["date-parts"]:
        year = pub_date["date-parts"][0][0]
        
    venue = None
    if "container-title" in item and item["container-title"]:
        venue = item["container-title"][0]
        
    return ScholarlyCandidate(
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=item.get("DOI"),
        source="Crossref",
        url=item.get("URL")
    )

def _map_openalex_item(item: Dict[str, Any]) -> ScholarlyCandidate:
    title = item.get("title") or item.get("display_name") or ""
    
    authors = []
    for authorship in item.get("authorships", []):
        author_info = authorship.get("author", {})
        display_name = author_info.get("display_name", "")
        if display_name:
            authors.append(display_name)
            
    year = item.get("publication_year")
    
    venue = None
    primary_location = item.get("primary_location") or {}
    source_info = primary_location.get("source") or {}
    if source_info and source_info.get("display_name"):
        venue = source_info.get("display_name")
        
    doi = item.get("doi")
    url = item.get("id") or doi
    
    return ScholarlyCandidate(
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
        source="OpenAlex",
        url=url
    )

def _map_s2_item(item: Dict[str, Any]) -> ScholarlyCandidate:
    title = item.get("title") or ""
    
    authors = []
    for author_info in item.get("authors", []):
        name = author_info.get("name", "")
        if name:
            authors.append(name)
            
    year = item.get("year")
    venue = item.get("venue") or ""
    
    doi = None
    external_ids = item.get("externalIds") or {}
    if "DOI" in external_ids:
        doi = external_ids["DOI"]
        
    url = item.get("url")
    
    return ScholarlyCandidate(
        title=title,
        authors=authors,
        year=year,
        venue=venue if venue else None,
        doi=doi,
        source="Semantic Scholar",
        url=url
    )

def _get_headers() -> Dict[str, str]:
    headers = {"User-Agent": "CiteCheck/1.0 (mailto:not_set)"}
    mailto = os.environ.get("CROSSREF_MAILTO")
    if mailto:
        headers["User-Agent"] = f"CiteCheck/1.0 (mailto:{mailto})"
    return headers

async def lookup_by_doi(doi: str) -> Optional[ScholarlyCandidate]:
    normalized_doi = normalize_doi(doi)
    
    cache_key = generate_key("Crossref", "doi", normalized_doi)
    hit, cached_cands = get_cached_candidates(cache_key)
    if hit:
        return cached_cands[0] if cached_cands else None

    url = f"{CROSSREF_API_URL}/{normalized_doi}"
    headers = _get_headers()
    params = {}
    mailto = os.environ.get("CROSSREF_MAILTO")
    if mailto:
        params["mailto"] = mailto
        
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 404:
                set_cached_candidates(cache_key, "Crossref", "doi", [])
                return None
            
            response.raise_for_status()
            data = response.json()
            
            if "message" in data:
                candidate = _map_crossref_item(data["message"])
                set_cached_candidates(cache_key, "Crossref", "doi", [candidate])
                return candidate
                
    except httpx.HTTPStatusError as e:
        logger.warning(f"Crossref API returned {e.response.status_code} for DOI {normalized_doi}")
    except httpx.RequestError as e:
        logger.error(f"Network error during Crossref DOI lookup: {e}")
    except ValueError as e:
        logger.error(f"Failed to parse Crossref JSON response for DOI {normalized_doi}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during Crossref DOI lookup: {e}")
        
    return None

async def search_by_bibliographic(title: str, first_author: str) -> List[ScholarlyCandidate]:
    query = title
    if first_author:
        query = f"{title} {first_author}"
        
    cache_key = generate_key("Crossref", "search", query.lower().strip())
    hit, cached_cands = get_cached_candidates(cache_key)
    if hit:
        return cached_cands

    headers = _get_headers()
    params = {
        "query.bibliographic": query,
        "rows": 3
    }
    
    mailto = os.environ.get("CROSSREF_MAILTO")
    if mailto:
        params["mailto"] = mailto
        
    candidates = []
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(CROSSREF_API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("message", {}).get("items", [])
            for item in items:
                try:
                    candidates.append(_map_crossref_item(item))
                except Exception as map_err:
                    logger.warning(f"Failed to map a Crossref item: {map_err}")
            
            set_cached_candidates(cache_key, "Crossref", "search", candidates)
            return candidates
            
    except httpx.HTTPStatusError as e:
        logger.warning(f"Crossref API returned {e.response.status_code} for bibliographic search")
    except httpx.RequestError as e:
        logger.error(f"Network error during Crossref bibliographic search: {e}")
    except ValueError as e:
        logger.error(f"Failed to parse Crossref JSON response for search: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during Crossref search: {e}")
        
    return candidates

async def search_openalex(title: str) -> List[ScholarlyCandidate]:
    cache_key = generate_key("OpenAlex", "search", title.lower().strip())
    hit, cached_cands = get_cached_candidates(cache_key)
    if hit:
        return cached_cands

    headers = {"User-Agent": "CiteCheck/1.0"}
    mailto = os.environ.get("OPENALEX_MAILTO")
    params = {
        "search": title,
        "per-page": 3
    }
    if mailto:
        params["mailto"] = mailto
        headers["User-Agent"] = f"CiteCheck/1.0 (mailto:{mailto})"
        
    candidates = []
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPENALEX_API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            for item in results:
                try:
                    candidates.append(_map_openalex_item(item))
                except Exception as map_err:
                    logger.warning(f"Failed to map an OpenAlex item: {map_err}")
                    
            set_cached_candidates(cache_key, "OpenAlex", "search", candidates)
            return candidates
            
    except httpx.HTTPStatusError as e:
        logger.warning(f"OpenAlex API returned {e.response.status_code} for search")
    except httpx.RequestError as e:
        logger.error(f"Network error during OpenAlex search: {e}")
    except ValueError as e:
        logger.error(f"Failed to parse OpenAlex JSON response: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during OpenAlex search: {e}")
        
    return candidates

async def search_semantic_scholar(title: str) -> List[ScholarlyCandidate]:
    cache_key = generate_key("Semantic Scholar", "search", title.lower().strip())
    hit, cached_cands = get_cached_candidates(cache_key)
    if hit:
        return cached_cands

    headers = {"User-Agent": "CiteCheck/1.0"}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
        
    params = {
        "query": title,
        "limit": 3,
        "fields": "title,authors,year,venue,externalIds,url"
    }
    
    candidates = []
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(S2_API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("data", [])
            for item in items:
                try:
                    candidates.append(_map_s2_item(item))
                except Exception as map_err:
                    logger.warning(f"Failed to map a Semantic Scholar item: {map_err}")
            
            set_cached_candidates(cache_key, "Semantic Scholar", "search", candidates)
            return candidates
            
    except httpx.HTTPStatusError as e:
        logger.warning(f"Semantic Scholar API returned {e.response.status_code} for search")
    except httpx.RequestError as e:
        logger.error(f"Network error during Semantic Scholar search: {e}")
    except ValueError as e:
        logger.error(f"Failed to parse Semantic Scholar JSON response: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during Semantic Scholar search: {e}")
        
    return candidates
