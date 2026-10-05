import unittest
import os
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lookup import search_semantic_scholar

class TestSemanticScholar(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.test_db = f"test_cache_s2_{os.getpid()}.db"
        self.patcher = patch.dict(os.environ, {"CITECHECK_CACHE_DB": self.test_db})
        self.patcher.start()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    @patch('lookup.httpx.AsyncClient')
    async def test_successful_s2_search(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "title": "Semantic Scholar Result 1",
                    "authors": [{"name": "Smith, J"}],
                    "year": 2020,
                    "venue": "Test Venue",
                    "externalIds": {"DOI": "10.123/s2"},
                    "url": "https://semanticscholar.org/paper/1"
                },
                {
                    "title": "Semantic Scholar Result 2"
                }
            ]
        }
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidates = await search_semantic_scholar("Semantic Scholar Result")
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].title, "Semantic Scholar Result 1")
        self.assertEqual(candidates[0].authors, ["Smith, J"])
        self.assertEqual(candidates[0].year, 2020)
        self.assertEqual(candidates[0].venue, "Test Venue")
        self.assertEqual(candidates[0].doi, "10.123/s2")
        self.assertEqual(candidates[0].source, "Semantic Scholar")
        self.assertEqual(candidates[0].url, "https://semanticscholar.org/paper/1")
        
        self.assertEqual(candidates[1].title, "Semantic Scholar Result 2")
        self.assertEqual(candidates[1].authors, [])
        self.assertEqual(candidates[1].year, None)

    @patch('lookup.httpx.AsyncClient')
    async def test_missing_metadata(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{}]
        }
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidates = await search_semantic_scholar("Empty")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "")
        self.assertEqual(candidates[0].source, "Semantic Scholar")

    @patch('lookup.httpx.AsyncClient')
    @patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "test-key-123"})
    async def test_api_key_configuration(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        await search_semantic_scholar("Test")
        
        args, kwargs = mock_client.get.call_args
        self.assertEqual(kwargs['headers'].get('x-api-key'), "test-key-123")
        self.assertEqual(kwargs['params']['limit'], 3)
        self.assertEqual(kwargs['params']['fields'], "title,authors,year,venue,externalIds,url")

    @patch('lookup.httpx.AsyncClient')
    async def test_network_failure(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Network Down", request=MagicMock())
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        candidates = await search_semantic_scholar("Test")
        self.assertEqual(len(candidates), 0)

    @patch('lookup.httpx.AsyncClient')
    async def test_rate_limit_handled(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        # httpx raise_for_status will raise HTTPStatusError
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("429 Too Many Requests", request=MagicMock(), response=mock_response)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidates = await search_semantic_scholar("Test")
        self.assertEqual(len(candidates), 0)

    @patch('lookup.httpx.AsyncClient')
    async def test_malformed_json_response(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Malformed JSON")
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidates = await search_semantic_scholar("Test")
        self.assertEqual(len(candidates), 0)

if __name__ == '__main__':
    unittest.main()
