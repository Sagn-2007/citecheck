import unittest
import os
import json
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extract import extract_references, ReferenceExtractionError, PROMPT_TEMPLATE

class TestExtract(unittest.TestCase):

    def setUp(self):
        self.patcher = patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123"})
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    @patch('extract.genai.Client')
    def test_single_reference_extraction(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "references": [
                {
                    "raw": "Smith, J. (2020). A test paper. Test Venue, 10.123/test.",
                    "authors": ["Smith, J."],
                    "title": "A test paper",
                    "year": 2020,
                    "venue": "Test Venue",
                    "doi": "10.123/test",
                    "type": "article"
                }
            ]
        })
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        refs = extract_references("Smith, J. (2020). A test paper. Test Venue, 10.123/test.")
        
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].raw, "Smith, J. (2020). A test paper. Test Venue, 10.123/test.")
        self.assertEqual(refs[0].authors, ["Smith, J."])
        self.assertEqual(refs[0].title, "A test paper")
        self.assertEqual(refs[0].year, 2020)
        self.assertEqual(refs[0].venue, "Test Venue")
        self.assertEqual(refs[0].doi, "10.123/test")
        self.assertEqual(refs[0].type.value, "article")
        
        args, kwargs = mock_client.models.generate_content.call_args
        self.assertEqual(kwargs['config'].temperature, 0.0)
        self.assertEqual(kwargs['config'].response_mime_type, "application/json")

    @patch('extract.genai.Client')
    def test_multiple_references(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "references": [
                {
                    "raw": "Ref 1",
                    "authors": ["A"],
                    "title": "T1",
                    "type": "article"
                },
                {
                    "raw": "Ref 2",
                    "authors": ["B"],
                    "title": "T2",
                    "type": "book"
                }
            ]
        })
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        refs = extract_references("Ref 1\nRef 2")
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0].title, "T1")
        self.assertEqual(refs[1].title, "T2")

    @patch('extract.genai.Client')
    def test_missing_optional_metadata(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "references": [
                {
                    "raw": "Bare ref",
                    "authors": [],
                    "title": "T1",
                    "year": None,
                    "venue": None,
                    "doi": None,
                    "type": "other"
                }
            ]
        })
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        refs = extract_references("Bare ref")
        self.assertEqual(len(refs), 1)
        self.assertIsNone(refs[0].year)
        self.assertIsNone(refs[0].doi)
        self.assertIsNone(refs[0].venue)
        self.assertEqual(refs[0].authors, [])

    @patch('extract.genai.Client')
    def test_malformed_json_retry_success(self, mock_client_cls):
        mock_client = MagicMock()
        
        bad_response = MagicMock()
        bad_response.text = "NOT JSON"
        
        good_response = MagicMock()
        good_response.text = json.dumps({
            "references": [
                {
                    "raw": "R1",
                    "authors": [],
                    "title": "T1",
                    "type": "article"
                }
            ]
        })
        
        mock_client.models.generate_content.side_effect = [bad_response, good_response]
        mock_client_cls.return_value = mock_client

        refs = extract_references("R1")
        self.assertEqual(len(refs), 1)
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    @patch('extract.genai.Client')
    def test_malformed_json_retry_failure(self, mock_client_cls):
        mock_client = MagicMock()
        bad_response = MagicMock()
        bad_response.text = "NOT JSON"
        mock_client.models.generate_content.return_value = bad_response
        mock_client_cls.return_value = mock_client

        with self.assertRaises(ReferenceExtractionError):
            extract_references("R1")
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    @patch('extract.genai.Client')
    def test_validation_failure_retry_success(self, mock_client_cls):
        mock_client = MagicMock()
        
        bad_response = MagicMock()
        # Invalid enum value "invalid_type"
        bad_response.text = json.dumps({
            "references": [
                {
                    "raw": "R1",
                    "authors": [],
                    "title": "T1",
                    "type": "invalid_type"
                }
            ]
        })
        
        good_response = MagicMock()
        good_response.text = json.dumps({
            "references": [
                {
                    "raw": "R1",
                    "authors": [],
                    "title": "T1",
                    "type": "article"
                }
            ]
        })
        
        mock_client.models.generate_content.side_effect = [bad_response, good_response]
        mock_client_cls.return_value = mock_client

        refs = extract_references("R1")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].type.value, "article")
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key(self):
        with self.assertRaises(ReferenceExtractionError) as context:
            extract_references("R1")
        self.assertIn("GEMINI_API_KEY environment variable is not set", str(context.exception))

    def test_prompt_does_not_ask_for_verification(self):
        self.assertIn("Do not verify whether references are real", PROMPT_TEMPLATE)
        self.assertIn("Do not search the internet", PROMPT_TEMPLATE)
        self.assertNotIn("verdict", PROMPT_TEMPLATE)
        self.assertNotIn("VERIFIED", PROMPT_TEMPLATE)

if __name__ == '__main__':
    unittest.main()
