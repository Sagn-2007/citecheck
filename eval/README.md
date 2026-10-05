# CiteCheck Evaluation Harness

This directory contains the deterministic evaluation framework for CiteCheck, designed to benchmark the deterministic scholarly matching engine without executing fragile, live-network LLM or scholarly API calls.

## Dataset Size and Composition

The evaluation dataset (`dataset.csv`) contains **145 references**, strictly expanded and partitioned into four explicit categories:

1. **Real References (45)**: Legitimate references mirroring existing baseline scholarly records. Tests variations like missing venues or minor typos.
2. **Corrupted References (75)**: Deterministically perturbed items testing exact matching boundaries:
   - `title_changed`: Major vs. minor typos. (Major perturbations strictly fail threshold and route to `NOT_FOUND`).
   - `author_changed`: First-author modifications (Strictly route to `MISMATCH`).
   - `year_changed`: `±1` year tolerance (Routes to `VERIFIED`) vs. `>1` year divergence (`MISMATCH`).
   - `venue_changed`: Tests field matching priority (Routes to `VERIFIED` since title/author/year dominate).
3. **Fabricated References (15)**: Hallucinated AI-style claims designed to route directly to `NOT_FOUND`.
4. **Edge Cases (10)**: Unsupported structures like URL references (`CANNOT_VERIFY`) and mangled DOIs (`DOI_INVALID`).

## Mock Provider Methodology

To ensure reproducible benchmarks, the execution runner (`run_eval.py`) completely intercepts HTTP interactions from `backend/lookup.py`. 
It intercepts DOIs and bibliographic searches, mapping them deterministically to the ground-truth arrays in `mock_db.json`. 
- **Fuzzy Lookups**: The mock searches employ `rapidfuzz` (minimum 60% similarity) to accurately simulate standard Scholarly API retrieval behaviors (where a single character typo in a title would still fetch the correct underlying candidate).

## Metrics Explained

- **Accuracy**: The percentage of predicted verdicts that exactly match the expected ground-truth labels.
- **Precision (VERIFIED)**: Of all references flagged as `VERIFIED`, the percentage that were truly legitimate.
- **Recall (VERIFIED)**: Of all genuinely legitimate references, the percentage that CiteCheck successfully verified.
- **Fabrication Catch Rate**: The percentage of completely hallucinated references that correctly triggered a `NOT_FOUND` block.
- **False-Flag Rate**: Legitimate references that were incorrectly rejected as mismatched or not found.

## How to Run

From the repository root, ensure your virtual environment is active, then execute:

```bash
source backend/venv/bin/activate
python eval/run_eval.py
```

The output is written to `eval/results.md`.

## Known Limitations

- **Gemini Extraction Omitted**: This seed evaluation isolates the deterministic matching engine. The `raw_reference` is parsed directly via dataset columns, bypassing the LLM extraction step. This guarantees metric stability but does not account for upstream hallucination/parsing drift.
- **Small Dataset**: While perfectly covering the algorithmic boundaries of `match.py`, 145 references is a deterministic benchmark, not a statistically exhaustive sample of all global citations.
