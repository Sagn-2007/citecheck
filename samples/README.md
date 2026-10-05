# CiteCheck Demo Samples

This directory contains carefully curated bibliography samples to demonstrate CiteCheck's capabilities during a live presentation. 
These examples use real-world well-known AI papers, interspersed with deliberate corruptions to test the verification boundaries.

## Files

1. **`demo_clean_bibliography.txt`**: A clean, valid list of real scholarly citations. This should yield 100% `VERIFIED` results (assuming API availability).
2. **`demo_mixed_bibliography.txt`**: A chaotic list designed to trigger the full spectrum of CiteCheck verdicts:
   - *Valid references* -> `VERIFIED`
   - *Fabricated reference* (e.g. "The future of quantum LLMs in interstellar networking") -> `NOT_FOUND`
   - *Corrupted metadata* (e.g. "Attention is all you need" from 1990) -> `MISMATCH`
   - *Invalid DOI* (e.g. `10.invalid/fake`) -> `DOI_INVALID`

## How to use

1. Ensure the backend and frontend are running.
2. Open the React frontend.
3. Select the **Paste Bibliography** mode.
4. Copy the entire contents of a sample file.
5. Paste into the text area and click **Verify Citations**.
6. Observe how the results are deterministically flagged and read the field-level comparisons for the mismatched items.
