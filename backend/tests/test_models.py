import unittest
from pydantic import ValidationError

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import (
    ExtractedReference,
    ReferenceType,
    ScholarlyCandidate,
    Verdict,
    FieldDifference,
    ReferenceResult,
    VerifyResponse
)

class TestModels(unittest.TestCase):
    def test_valid_extracted_reference(self):
        ref = ExtractedReference(
            raw="Smith, J. (2021). A good paper. Journal of Science.",
            authors=["Smith, J."],
            title="A good paper",
            year=2021,
            venue="Journal of Science",
            type="article"
        )
        self.assertEqual(ref.title, "A good paper")
        self.assertEqual(ref.type, ReferenceType.ARTICLE)

    def test_invalid_reference_type(self):
        with self.assertRaises(ValidationError):
            ExtractedReference(
                raw="...",
                authors=[],
                title="...",
                type="invalid_type"
            )

    def test_field_difference(self):
        diff = FieldDifference(
            field_name="year",
            submitted=2021,
            matched=2020
        )
        self.assertEqual(diff.submitted, 2021)
        self.assertEqual(diff.matched, 2020)

    def test_verification_result(self):
        ref = ExtractedReference(
            raw="...",
            authors=["Author"],
            title="Title",
            type="book"
        )
        candidate = ScholarlyCandidate(
            title="Title",
            authors=["Author"],
            source="Crossref"
        )
        result = ReferenceResult(
            extracted_reference=ref,
            verdict=Verdict.VERIFIED,
            closest_candidate=candidate,
            similarity=0.95,
            field_differences=[]
        )
        self.assertEqual(result.verdict, Verdict.VERIFIED)
        self.assertIsNotNone(result.closest_candidate)

    def test_verify_response(self):
        ref = ExtractedReference(
            raw="...",
            authors=[],
            title="...",
            type="other"
        )
        res = ReferenceResult(
            extracted_reference=ref,
            verdict=Verdict.NOT_FOUND
        )
        response = VerifyResponse(
            results=[res],
            total_references=1,
            verdict_counts={Verdict.NOT_FOUND: 1},
            reliability_score=0.0
        )
        self.assertEqual(response.total_references, 1)
        self.assertEqual(response.results[0].verdict, Verdict.NOT_FOUND)
        self.assertEqual(response.verdict_counts[Verdict.NOT_FOUND], 1)

if __name__ == '__main__':
    unittest.main()
