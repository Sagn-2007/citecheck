import unittest
import os
from unittest.mock import patch, AsyncMock
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import ExtractedReference, ScholarlyCandidate, ReferenceType, Verdict
from verify_one import verify_reference, _select_best_candidate

class TestVerifyOne(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.ref_with_doi = ExtractedReference(
            raw="Raw ref",
            authors=["Smith, John"],
            title="A standard test paper for citation verification",
            year=2020,
            doi="10.123/abc",
            type=ReferenceType.ARTICLE
        )
        self.ref_no_doi = ExtractedReference(
            raw="Raw ref",
            authors=["Smith, John"],
            title="A standard test paper for citation verification",
            year=2020,
            type=ReferenceType.ARTICLE
        )
        self.good_cand = ScholarlyCandidate(
            title="A standard test paper for citation verification",
            authors=["Smith, John"],
            year=2020,
            doi="10.123/abc",
            source="Crossref"
        )
        self.bad_author_cand = ScholarlyCandidate(
            title="A standard test paper for citation verification",
            authors=["Doe, Jane"],
            year=2020,
            doi="10.123/abc",
            source="Crossref"
        )
        self.weak_cand = ScholarlyCandidate(
            title="Some other random paper completely unrelated",
            authors=["Johnson, M"],
            year=2021,
            source="Crossref"
        )

    @patch('verify_one.lookup_by_doi')
    async def test_valid_doi_verified(self, mock_lookup):
        mock_lookup.return_value = self.good_cand
        result = await verify_reference(self.ref_with_doi)
        self.assertEqual(result.verdict, Verdict.VERIFIED)
        mock_lookup.assert_called_once_with("10.123/abc")

    @patch('verify_one.lookup_by_doi')
    async def test_valid_doi_mismatch(self, mock_lookup):
        mock_lookup.return_value = self.bad_author_cand
        result = await verify_reference(self.ref_with_doi)
        self.assertEqual(result.verdict, Verdict.MISMATCH)

    @patch('verify_one.lookup_by_doi')
    async def test_doi_invalid(self, mock_lookup):
        mock_lookup.return_value = None
        result = await verify_reference(self.ref_with_doi)
        self.assertEqual(result.verdict, Verdict.DOI_INVALID)

    @patch('verify_one.search_by_bibliographic')
    async def test_no_doi_strong_candidate_verified(self, mock_search):
        mock_search.return_value = [self.good_cand]
        result = await verify_reference(self.ref_no_doi)
        self.assertEqual(result.verdict, Verdict.VERIFIED)
        mock_search.assert_called_once_with("A standard test paper for citation verification", "Smith, John")

    @patch('verify_one.search_by_bibliographic')
    async def test_no_doi_wrong_metadata_mismatch(self, mock_search):
        mock_search.return_value = [self.bad_author_cand]
        result = await verify_reference(self.ref_no_doi)
        self.assertEqual(result.verdict, Verdict.MISMATCH)

    @patch('verify_one.search_by_bibliographic')
    async def test_no_doi_no_candidates_not_found(self, mock_search):
        mock_search.return_value = []
        result = await verify_reference(self.ref_no_doi)
        self.assertEqual(result.verdict, Verdict.NOT_FOUND)
        
    @patch('verify_one.search_by_bibliographic')
    async def test_multiple_candidates_selection(self, mock_search):
        # Even if the good candidate is last, it should be selected.
        mock_search.return_value = [self.weak_cand, self.bad_author_cand, self.good_cand]
        result = await verify_reference(self.ref_no_doi)
        
        self.assertEqual(result.verdict, Verdict.VERIFIED)
        self.assertEqual(result.closest_candidate.authors, ["Smith, John"])

    @patch('verify_one.search_by_bibliographic')
    async def test_missing_optional_metadata(self, mock_search):
        # No author or year in reference
        ref_sparse = ExtractedReference(
            raw="Raw ref",
            authors=[],
            title="A standard test paper for citation verification",
            type=ReferenceType.ARTICLE
        )
        mock_search.return_value = [self.good_cand]
        result = await verify_reference(ref_sparse)
        
        # Author will fail to match because sub_author is empty, resulting in MISMATCH
        self.assertEqual(result.verdict, Verdict.MISMATCH)
        mock_search.assert_called_once_with("A standard test paper for citation verification", "")

    @patch('verify_one.search_semantic_scholar')
    @patch('verify_one.search_openalex')
    @patch('verify_one.search_by_bibliographic')
    async def test_crossref_success_no_openalex_or_s2(self, mock_search, mock_oa, mock_s2):
        mock_search.return_value = [self.good_cand]
        result = await verify_reference(self.ref_no_doi)
        self.assertEqual(result.verdict, Verdict.VERIFIED)
        mock_oa.assert_not_called()
        mock_s2.assert_not_called()

    @patch('verify_one.search_semantic_scholar')
    @patch('verify_one.search_openalex')
    @patch('verify_one.search_by_bibliographic')
    async def test_crossref_fails_openalex_succeeds_no_s2(self, mock_search, mock_oa, mock_s2):
        mock_search.return_value = []
        
        oa_cand = self.good_cand.model_copy(update={"source": "OpenAlex"})
        mock_oa.return_value = [oa_cand]
        
        result = await verify_reference(self.ref_no_doi)
        self.assertEqual(result.verdict, Verdict.VERIFIED)
        self.assertEqual(result.closest_candidate.source, "OpenAlex")
        mock_oa.assert_called_once()
        mock_s2.assert_not_called()
        
    @patch('verify_one.search_semantic_scholar')
    @patch('verify_one.search_openalex')
    @patch('verify_one.search_by_bibliographic')
    async def test_both_fail_s2_succeeds(self, mock_search, mock_oa, mock_s2):
        mock_search.return_value = [self.weak_cand]
        mock_oa.return_value = []
        
        s2_cand = self.good_cand.model_copy(update={"source": "Semantic Scholar"})
        mock_s2.return_value = [s2_cand]
        
        result = await verify_reference(self.ref_no_doi)
        self.assertEqual(result.verdict, Verdict.VERIFIED)
        self.assertEqual(result.closest_candidate.source, "Semantic Scholar")
        mock_oa.assert_called_once()
        mock_s2.assert_called_once()
        
    @patch('verify_one.search_semantic_scholar')
    @patch('verify_one.search_openalex')
    @patch('verify_one.search_by_bibliographic')
    async def test_all_sources_pooled_strongest_selected(self, mock_search, mock_oa, mock_s2):
        # Crossref gives a weak candidate
        mock_search.return_value = [self.weak_cand]
        
        # OpenAlex gives another weak candidate
        oa_cand = self.weak_cand.model_copy(update={"source": "OpenAlex"})
        mock_oa.return_value = [oa_cand]
        
        # S2 gives a great candidate (verified)
        s2_cand = self.good_cand.model_copy(update={"source": "Semantic Scholar"})
        mock_s2.return_value = [s2_cand]
        
        result = await verify_reference(self.ref_no_doi)
        
        # Should pick S2 candidate because it scores the highest
        self.assertEqual(result.verdict, Verdict.VERIFIED)
        self.assertEqual(result.closest_candidate.source, "Semantic Scholar")
        
    @patch('verify_one.search_semantic_scholar')
    @patch('verify_one.search_openalex')
    @patch('verify_one.lookup_by_doi')
    async def test_doi_invalid_fallbacks_not_called(self, mock_lookup, mock_oa, mock_s2):
        mock_lookup.return_value = None
        result = await verify_reference(self.ref_with_doi)
        self.assertEqual(result.verdict, Verdict.DOI_INVALID)
        mock_oa.assert_not_called()
        mock_s2.assert_not_called()

if __name__ == '__main__':
    unittest.main()
