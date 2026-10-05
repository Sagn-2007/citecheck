import unittest
import os
import sys
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from models import Verdict, ReferenceResult, ExtractedReference, FieldDifference, ScholarlyCandidate

client = TestClient(app)

class TestEndToEnd(unittest.TestCase):

    @patch('main.verify_reference', new_callable=AsyncMock)
    @patch('main.extract_references')
    def test_full_pipeline_all_verdicts(self, mock_extract, mock_verify):
        # We will mock extract_references to return 5 parsed references
        refs = [
            ExtractedReference(raw="Ref 1", authors=["A"], title="T1", type="article"),
            ExtractedReference(raw="Ref 2", authors=["B"], title="T2", type="article"),
            ExtractedReference(raw="Ref 3", authors=["C"], title="T3", type="article"),
            ExtractedReference(raw="Ref 4", authors=["D"], title="T4", type="article", doi="invalid"),
            ExtractedReference(raw="Ref 5", authors=["E"], title="T5", type="other"),
        ]
        mock_extract.return_value = refs

        # We will mock verify_one to return the 5 respective results
        mock_verify.side_effect = [
            ReferenceResult(extracted_reference=refs[0], verdict=Verdict.VERIFIED),
            ReferenceResult(extracted_reference=refs[1], verdict=Verdict.MISMATCH, field_differences=[FieldDifference(field_name="title", submitted="T2", matched="T2_mismatch")]),
            ReferenceResult(extracted_reference=refs[2], verdict=Verdict.NOT_FOUND),
            ReferenceResult(extracted_reference=refs[3], verdict=Verdict.DOI_INVALID),
            ReferenceResult(extracted_reference=refs[4], verdict=Verdict.CANNOT_VERIFY),
        ]

        response = client.post("/verify", json={"text": "Raw bibliography with 5 types"})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["total_references"], 5)
        self.assertEqual(data["verdict_counts"]["VERIFIED"], 1)
        self.assertEqual(data["verdict_counts"]["MISMATCH"], 1)
        self.assertEqual(data["verdict_counts"]["NOT_FOUND"], 1)
        self.assertEqual(data["verdict_counts"]["DOI_INVALID"], 1)
        self.assertEqual(data["verdict_counts"]["CANNOT_VERIFY"], 1)
        
        # Reliability score = 1 verified / 4 checkable = 0.25
        self.assertEqual(data["reliability_score"], 0.25)

if __name__ == '__main__':
    unittest.main()
