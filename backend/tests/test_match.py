import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import ExtractedReference, ScholarlyCandidate, ReferenceType, Verdict
from match import compare_reference, compare_authors

class TestMatch(unittest.TestCase):

    def setUp(self):
        self.base_ref = ExtractedReference(
            raw="Example raw",
            authors=["Smith, John", "Doe, Jane"],
            title="A standard test paper for citation verification",
            year=2020,
            venue="Journal of Testing",
            doi="10.123/abc",
            type=ReferenceType.ARTICLE
        )
        self.base_candidate = ScholarlyCandidate(
            title="A standard test paper for citation verification",
            authors=["Smith, John", "Doe, Jane"],
            year=2020,
            venue="Journal of Testing",
            doi="10.123/abc",
            source="Test"
        )

    def test_identical_reference(self):
        result = compare_reference(self.base_ref, self.base_candidate)
        self.assertEqual(result.verdict, Verdict.VERIFIED)

    def test_author_differs_mismatch(self):
        cand = self.base_candidate.model_copy(update={"authors": ["Johnson, Mark"]})
        result = compare_reference(self.base_ref, cand)
        self.assertEqual(result.verdict, Verdict.MISMATCH)

    def test_year_differs_by_more_than_1(self):
        cand = self.base_candidate.model_copy(update={"year": 2018})
        result = compare_reference(self.base_ref, cand)
        self.assertEqual(result.verdict, Verdict.MISMATCH)

    def test_year_differs_by_1(self):
        cand = self.base_candidate.model_copy(update={"year": 2019})
        result = compare_reference(self.base_ref, cand)
        self.assertEqual(result.verdict, Verdict.VERIFIED)

    def test_low_title_similarity(self):
        cand = self.base_candidate.model_copy(update={"title": "Completely unrelated paper about something else"})
        result = compare_reference(self.base_ref, cand)
        self.assertEqual(result.verdict, Verdict.NOT_FOUND)

    def test_invalid_doi_status(self):
        result = compare_reference(self.base_ref, self.base_candidate, doi_status="invalid")
        self.assertEqual(result.verdict, Verdict.DOI_INVALID)

    def test_field_differences(self):
        cand = self.base_candidate.model_copy(update={
            "year": 2015,
            "authors": ["Someone, Else"]
        })
        result = compare_reference(self.base_ref, cand)
        self.assertEqual(result.verdict, Verdict.MISMATCH)
        diff_fields = {d.field_name for d in result.field_differences}
        self.assertIn("year", diff_fields)
        self.assertIn("authors", diff_fields)

    def test_author_initials(self):
        # Author matching with initials
        ref = self.base_ref.model_copy(update={"authors": ["Smith, J."]})
        cand = self.base_candidate.model_copy(update={"authors": ["Smith, John"]})
        result = compare_reference(ref, cand)
        self.assertEqual(result.verdict, Verdict.VERIFIED)

    def test_author_order_insensitive(self):
        ref = self.base_ref.model_copy(update={"authors": ["Doe, Jane", "Smith, John"]})
        cand = self.base_candidate.model_copy(update={"authors": ["Smith, John", "Doe, Jane"]})
        result = compare_reference(ref, cand)
        self.assertEqual(result.verdict, Verdict.VERIFIED)
        
    def test_missing_optional_venue(self):
        ref = self.base_ref.model_copy(update={"venue": None})
        cand = self.base_candidate.model_copy(update={"venue": None})
        result = compare_reference(ref, cand)
        self.assertEqual(result.verdict, Verdict.VERIFIED)

if __name__ == '__main__':
    unittest.main()
