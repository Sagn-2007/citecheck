import unittest
import os
import sqlite3
from unittest.mock import patch
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cache import generate_key, get_cached_candidates, set_cached_candidates, init_db
from models import ScholarlyCandidate
from lookup import normalize_doi

class TestCache(unittest.TestCase):

    def setUp(self):
        self.test_db = "test_cache.db"
        self.patcher = patch.dict(os.environ, {"CITECHECK_CACHE_DB": self.test_db})
        self.patcher.start()
        # Ensure clean state
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_initialization(self):
        init_db()
        self.assertTrue(os.path.exists(self.test_db))
        # Verify schema
        conn = sqlite3.connect(self.test_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cache_entries'")
            self.assertIsNotNone(cursor.fetchone())
        finally:
            conn.close()

    def test_cache_miss(self):
        hit, cands = get_cached_candidates("nonexistent")
        self.assertFalse(hit)
        self.assertEqual(cands, [])

    def test_cache_set_get(self):
        cands = [ScholarlyCandidate(title="Test", authors=["Author"], source="test")]
        set_cached_candidates("key1", "test_source", "search", cands)
        
        hit, retrieved = get_cached_candidates("key1")
        self.assertTrue(hit)
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0].title, "Test")

    def test_cache_empty_list(self):
        set_cached_candidates("key_empty", "test_source", "search", [])
        hit, retrieved = get_cached_candidates("key_empty")
        self.assertTrue(hit)
        self.assertEqual(retrieved, [])

    def test_cache_keys_deterministic(self):
        key1 = generate_key("Crossref", "doi", "10.123/abc")
        key2 = generate_key("Crossref", "doi", "10.123/abc")
        self.assertEqual(key1, key2)

    def test_different_sources_different_keys(self):
        key1 = generate_key("Crossref", "doi", "10.123/abc")
        key2 = generate_key("OpenAlex", "doi", "10.123/abc")
        self.assertNotEqual(key1, key2)

    def test_different_query_types_different_keys(self):
        key1 = generate_key("Crossref", "doi", "10.123/abc")
        key2 = generate_key("Crossref", "search", "10.123/abc")
        self.assertNotEqual(key1, key2)

    def test_doi_normalization_keys(self):
        raw1 = "https://doi.org/10.123/abc"
        raw2 = "doi:10.123/abc"
        key1 = generate_key("Crossref", "doi", normalize_doi(raw1))
        key2 = generate_key("Crossref", "doi", normalize_doi(raw2))
        self.assertEqual(key1, key2)

    def test_cache_survives_reopen(self):
        cands = [ScholarlyCandidate(title="Survive", authors=[], source="test")]
        set_cached_candidates("survive_key", "test", "search", cands)
        
        # Simulate reopen (no connection pooling active across calls)
        hit, retrieved = get_cached_candidates("survive_key")
        self.assertTrue(hit)
        self.assertEqual(retrieved[0].title, "Survive")

if __name__ == '__main__':
    unittest.main()
