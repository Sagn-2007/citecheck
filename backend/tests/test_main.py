import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from models import Verdict, ReferenceResult, ExtractedReference, ReferenceType

client = TestClient(app)

class TestMainAPI(unittest.TestCase):

    def setUp(self):
        self.valid_ref_dict = {
            "raw": "Smith, J. A standard test paper for citation verification.",
            "authors": ["Smith, John"],
            "title": "A standard test paper for citation verification",
            "year": 2020,
            "type": "article"
        }
        self.mock_result_verified = ReferenceResult(
            extracted_reference=ExtractedReference(**self.valid_ref_dict),
            verdict=Verdict.VERIFIED
        )
        self.mock_result_cannot_verify = ReferenceResult(
            extracted_reference=ExtractedReference(**self.valid_ref_dict),
            verdict=Verdict.CANNOT_VERIFY
        )

    def test_get_root(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "CiteCheck backend is running"})

    @patch('main.verify_reference', new_callable=AsyncMock)
    def test_verify_single_reference(self, mock_verify):
        mock_verify.return_value = self.mock_result_verified
        
        response = client.post("/verify", json={
            "references": [self.valid_ref_dict]
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_references"], 1)
        self.assertEqual(data["verdict_counts"][Verdict.VERIFIED], 1)
        self.assertEqual(data["reliability_score"], 1.0)
        
        mock_verify.assert_called_once()

    @patch('main.verify_reference', new_callable=AsyncMock)
    def test_verify_multiple_references(self, mock_verify):
        # Return VERIFIED for first, CANNOT_VERIFY for second
        mock_verify.side_effect = [self.mock_result_verified, self.mock_result_cannot_verify]
        
        response = client.post("/verify", json={
            "references": [self.valid_ref_dict, self.valid_ref_dict]
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_references"], 2)
        self.assertEqual(data["verdict_counts"][Verdict.VERIFIED], 1)
        self.assertEqual(data["verdict_counts"][Verdict.CANNOT_VERIFY], 1)
        
        # 1 verified / 1 checkable (because 1 was CANNOT_VERIFY)
        self.assertEqual(data["reliability_score"], 1.0)

    def test_empty_references(self):
        response = client.post("/verify", json={
            "references": []
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_references"], 0)
        self.assertIsNone(data["reliability_score"])

    def test_malformed_request_body(self):
        response = client.post("/verify", json={
            "wrong_field": []
        })
        self.assertEqual(response.status_code, 422)

    def test_invalid_reference_type(self):
        bad_ref = self.valid_ref_dict.copy()
        bad_ref["type"] = "unsupported_type"
        
        response = client.post("/verify", json={
            "references": [bad_ref]
        })
        self.assertEqual(response.status_code, 422)

    @patch('main.verify_reference', new_callable=AsyncMock)
    def test_doi_invalid_handling(self, mock_verify):
        mock_res = ReferenceResult(
            extracted_reference=ExtractedReference(**self.valid_ref_dict),
            verdict=Verdict.DOI_INVALID
        )
        mock_verify.return_value = mock_res
        
        response = client.post("/verify", json={
            "references": [self.valid_ref_dict]
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["verdict_counts"][Verdict.DOI_INVALID], 1)
        self.assertEqual(data["reliability_score"], 0.0)

    @patch('main.extract_references')
    @patch('main.verify_reference', new_callable=AsyncMock)
    def test_raw_text_success(self, mock_verify, mock_extract):
        ext_ref = ExtractedReference(**self.valid_ref_dict)
        mock_extract.return_value = [ext_ref]
        mock_verify.return_value = self.mock_result_verified
        
        response = client.post("/verify", json={"text": "Raw bibliography string"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_references"], 1)
        self.assertEqual(data["verdict_counts"][Verdict.VERIFIED], 1)
        
        mock_extract.assert_called_once_with("Raw bibliography string")
        mock_verify.assert_called_once_with(ext_ref)

    @patch('main.extract_references')
    @patch('main.verify_reference', new_callable=AsyncMock)
    def test_raw_text_multiple_preserves_order(self, mock_verify, mock_extract):
        ext_ref1 = ExtractedReference(**self.valid_ref_dict)
        ext_ref2 = ExtractedReference(**self.valid_ref_dict)
        mock_extract.return_value = [ext_ref1, ext_ref2]
        
        mock_verify.side_effect = [self.mock_result_verified, self.mock_result_cannot_verify]
        
        response = client.post("/verify", json={"text": "Multiple raw"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Ensure order is preserved
        self.assertEqual(data["results"][0]["verdict"], "VERIFIED")
        self.assertEqual(data["results"][1]["verdict"], "CANNOT_VERIFY")

    def test_reject_both_text_and_references(self):
        response = client.post("/verify", json={
            "text": "Raw text",
            "references": [self.valid_ref_dict]
        })
        self.assertEqual(response.status_code, 422)

    def test_reject_neither(self):
        response = client.post("/verify", json={})
        self.assertEqual(response.status_code, 422)

    def test_reject_empty_text(self):
        response = client.post("/verify", json={"text": ""})
        self.assertEqual(response.status_code, 422)
        
        response2 = client.post("/verify", json={"text": "   \n"})
        self.assertEqual(response2.status_code, 422)

    @patch('main.extract_references')
    def test_extraction_error_produces_500(self, mock_extract):
        from extract import ReferenceExtractionError
        mock_extract.side_effect = ReferenceExtractionError("Gemini is down")
        
        response = client.post("/verify", json={"text": "Raw text"})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Gemini is down")

    @patch('main.extract_document_text')
    @patch('main.extract_references')
    @patch('main.verify_reference', new_callable=AsyncMock)
    def test_pdf_upload_success(self, mock_verify, mock_extract_refs, mock_extract_doc):
        mock_extract_doc.return_value = "Parsed PDF Text"
        ext_ref = ExtractedReference(**self.valid_ref_dict)
        mock_extract_refs.return_value = [ext_ref]
        mock_verify.return_value = self.mock_result_verified
        
        response = client.post("/verify", files={"file": ("test.pdf", b"pdfbytes", "application/pdf")})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_references"], 1)
        self.assertEqual(data["verdict_counts"]["VERIFIED"], 1)
        
        mock_extract_doc.assert_called_once_with(b"pdfbytes", "test.pdf", "application/pdf")
        mock_extract_refs.assert_called_once_with("Parsed PDF Text")
        mock_verify.assert_called_once_with(ext_ref)

    @patch('main.extract_document_text')
    @patch('main.extract_references')
    @patch('main.verify_reference', new_callable=AsyncMock)
    def test_docx_upload_success(self, mock_verify, mock_extract_refs, mock_extract_doc):
        mock_extract_doc.return_value = "Parsed DOCX Text"
        ext_ref = ExtractedReference(**self.valid_ref_dict)
        mock_extract_refs.return_value = [ext_ref]
        mock_verify.return_value = self.mock_result_verified
        
        response = client.post("/verify", files={"file": ("test.docx", b"docxbytes", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
        self.assertEqual(response.status_code, 200)

    def test_unsupported_upload_extension(self):
        # We don't even need to mock if it's caught by parser
        response = client.post("/verify", files={"file": ("test.txt", b"txtbytes", "text/plain")})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.json()["detail"])

    @patch('main.extract_document_text')
    def test_empty_extractable_text(self, mock_extract_doc):
        from document_parser import DocumentExtractionError
        mock_extract_doc.side_effect = DocumentExtractionError("No extractable text")
        response = client.post("/verify", files={"file": ("test.pdf", b"pdfbytes", "application/pdf")})
        self.assertEqual(response.status_code, 400)
        self.assertIn("No extractable text", response.json()["detail"])

    def test_file_size_limit(self):
        with patch.dict(os.environ, {"CITECHECK_MAX_UPLOAD_MB": "0"}):
            # 0 MB limit, so even 1 byte should fail
            response = client.post("/verify", files={"file": ("test.pdf", b"a", "application/pdf")})
            self.assertEqual(response.status_code, 413)

    def test_unsupported_content_type(self):
        response = client.post("/verify", data="plain text", headers={"content-type": "text/plain"})
        self.assertEqual(response.status_code, 415)

if __name__ == '__main__':
    unittest.main()
