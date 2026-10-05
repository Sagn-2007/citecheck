import unittest
import os
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lookup import lookup_by_doi, search_by_bibliographic, normalize_doi

class TestLookup(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.test_db = f"test_cache_lookup_{os.getpid()}.db"
        self.patcher = patch.dict(os.environ, {"CITECHECK_CACHE_DB": self.test_db})
        self.patcher.start()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_normalize_doi(self):
        self.assertEqual(normalize_doi("10.123/abc"), "10.123/abc")
        self.assertEqual(normalize_doi("https://doi.org/10.123/abc"), "10.123/abc")
        self.assertEqual(normalize_doi("http://dx.doi.org/10.123/abc"), "10.123/abc")
        self.assertEqual(normalize_doi("doi:10.123/abc"), "10.123/abc")

    @patch('lookup.httpx.AsyncClient')
    async def test_successful_doi_lookup(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["A Test Paper"],
                "author": [{"given": "Jane", "family": "Doe"}],
                "published": {"date-parts": [[2021]]},
                "DOI": "10.123/abc"
            }
        }
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidate = await lookup_by_doi("10.123/abc")
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.title, "A Test Paper")
        self.assertEqual(candidate.authors, ["Doe, Jane"])
        self.assertEqual(candidate.year, 2021)
        self.assertEqual(candidate.doi, "10.123/abc")

    @patch('lookup.httpx.AsyncClient')
    async def test_doi_not_found(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidate = await lookup_by_doi("10.123/abc")
        self.assertIsNone(candidate)

    @patch('lookup.httpx.AsyncClient')
    async def test_successful_bibliographic_search(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "items": [
                    {
                        "title": ["Search Result 1"],
                        "author": [{"family": "Smith"}],
                        "published": {"date-parts": [[2020]]}
                    },
                    {
                        "title": ["Search Result 2"]
                    }
                ]
            }
        }
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidates = await search_by_bibliographic("Search Result", "Smith")
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].title, "Search Result 1")
        self.assertEqual(candidates[1].title, "Search Result 2")
        
    @patch('lookup.httpx.AsyncClient')
    async def test_missing_crossref_metadata(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "items": [{}]
            }
        }
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidates = await search_by_bibliographic("Empty", "Test")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "")
        self.assertEqual(candidates[0].year, None)
        self.assertEqual(candidates[0].authors, [])

    @patch('lookup.httpx.AsyncClient')
    @patch.dict(os.environ, {"CROSSREF_MAILTO": "test@example.com"})
    async def test_mailto_configuration(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        await lookup_by_doi("10.123/abc")
        
        args, kwargs = mock_client.get.call_args
        self.assertEqual(kwargs['params'].get('mailto'), "test@example.com")
        self.assertIn("test@example.com", kwargs['headers']['User-Agent'])

    @patch('lookup.httpx.AsyncClient')
    async def test_network_failure(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Network Down", request=MagicMock())
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidate = await lookup_by_doi("10.123/abc")
        self.assertIsNone(candidate)
        
        candidates = await search_by_bibliographic("Test", "Author")
        self.assertEqual(len(candidates), 0)

    @patch('lookup.httpx.AsyncClient')
    async def test_malformed_json_response(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Malformed JSON")
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidate = await lookup_by_doi("10.123/abc")
        self.assertIsNone(candidate)

if __name__ == '__main__':
    unittest.main()
