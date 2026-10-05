import os
import sqlite3
import json
import hashlib
from typing import List, Optional, Tuple, Any
from models import ScholarlyCandidate

def get_db_path() -> str:
    default_path = os.path.join(os.path.dirname(__file__), "cache.db")
    return os.environ.get("CITECHECK_CACHE_DB", default_path)

def init_db():
    path = get_db_path()
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                source TEXT,
                query_type TEXT,
                response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    finally:
        conn.close()

def generate_key(source: str, query_type: str, query: str) -> str:
    raw = f"{source}:{query_type}:{query}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def get_cached_candidates(key: str) -> Tuple[bool, List[ScholarlyCandidate]]:
    """
    Returns (hit, candidates).
    hit is True if the key was found in the cache.
    candidates is the list of cached candidates (can be empty).
    """
    path = get_db_path()
    init_db()
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT response FROM cache_entries WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        if row is None:
            return False, []
            
        try:
            data = json.loads(row[0])
            candidates = [ScholarlyCandidate(**item) for item in data]
            return True, candidates
        except Exception:
            return False, []
    finally:
        conn.close()

def set_cached_candidates(key: str, source: str, query_type: str, candidates: List[ScholarlyCandidate]):
    path = get_db_path()
    init_db()
    data = [cand.model_dump() for cand in candidates]
    response_json = json.dumps(data)
    
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO cache_entries (key, source, query_type, response)
            VALUES (?, ?, ?, ?)
        ''', (key, source, query_type, response_json))
        conn.commit()
    finally:
        conn.close()
