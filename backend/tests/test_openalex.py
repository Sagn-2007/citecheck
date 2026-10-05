import unittest
import os
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lookup import search_openalex

class TestOpenAlex(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.test_db = f"test_cache_oa_{os.getpid()}.db"
        self.patcher = patch.dict(os.environ, {"CITECHECK_CACHE_DB": self.test_db})
        self.patcher.start()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    @patch('lookup.httpx.AsyncClient')
    async def test_successful_openalex_search(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "OpenAlex Result 1",
                    "authorships": [{"author": {"display_name": "Smith, J"}}],
                    "publication_year": 2020,
                    "primary_location": {"source": {"display_name": "Open Venue"}},
                    "doi": "10.123/oa1",
                    "id": "https://openalex.org/W1"
                },
                {
                    "display_name": "OpenAlex Result 2"
                }
            ]
        }
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidates = await search_openalex("OpenAlex Result")
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].title, "OpenAlex Result 1")
        self.assertEqual(candidates[0].authors, ["Smith, J"])
        self.assertEqual(candidates[0].year, 2020)
        self.assertEqual(candidates[0].venue, "Open Venue")
        self.assertEqual(candidates[0].doi, "10.123/oa1")
        self.assertEqual(candidates[0].source, "OpenAlex")
        
        self.assertEqual(candidates[1].title, "OpenAlex Result 2")
        self.assertEqual(candidates[1].authors, [])
        self.assertEqual(candidates[1].year, None)

    @patch('lookup.httpx.AsyncClient')
    async def test_missing_metadata(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{}]
        }
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidates = await search_openalex("Empty")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "")
        self.assertEqual(candidates[0].source, "OpenAlex")

    @patch('lookup.httpx.AsyncClient')
    @patch.dict(os.environ, {"OPENALEX_MAILTO": "oa@example.com"})
    async def test_mailto_configuration(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        await search_openalex("Test")
        
        args, kwargs = mock_client.get.call_args
        self.assertEqual(kwargs['params'].get('mailto'), "oa@example.com")
        self.assertIn("oa@example.com", kwargs['headers']['User-Agent'])

    @patch('lookup.httpx.AsyncClient')
    async def test_network_failure(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Network Down", request=MagicMock())
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        candidates = await search_openalex("Test")
        self.assertEqual(len(candidates), 0)

    @patch('lookup.httpx.AsyncClient')
    async def test_malformed_json_response(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Malformed JSON")
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        candidates = await search_openalex("Test")
        self.assertEqual(len(candidates), 0)

if __name__ == '__main__':
    unittest.main()
