# CiteCheck

CiteCheck is an AI-powered citation verifier for research reports that parses messy bibliographies (using Gemini) and strictly checks them against deterministic scholarly databases (Crossref, OpenAlex, Semantic Scholar) to flag hallucinatory claims and corrupted metadata.

## Demo Configuration

1. Copy `.env.example` to a new file named `.env` in the root directory.
2. Edit `.env` to add your **required** `GEMINI_API_KEY`.
3. (Optional) Add your email to `CROSSREF_MAILTO` and `OPENALEX_MAILTO` to use their faster polite pools.
4. (Optional) Add `SEMANTIC_SCHOLAR_API_KEY` to prevent rate limits.

### 1. Start the Backend
```bash
cd backend
source venv/bin/activate
# Make sure .env is loaded (if running manually, you can export or let the app handle it if dotenv is used)
# Note: The backend natively reads environment variables. If you export them in your shell, it works instantly.
export $(grep -v '^#' ../.env | xargs)
uvicorn main:app --reload
```

### 2. Start the Frontend
In a new terminal:
```bash
cd frontend
npm run dev
```

### 3. Verify Citations
1. Open the frontend in your browser (usually `http://localhost:5173`).
2. Select **Paste Bibliography** or **Upload PDF / DOCX**.
3. *Tip: You can paste the contents of `samples/demo_mixed_bibliography.txt`.*
4. Click **Verify Citations**.
5. Expand the cards to inspect the verdict explanations and exact mismatched fields.

## Project Structure
- `backend/`: FastAPI backend service (Extraction, matching, caching).
- `frontend/`: React + Vite frontend application.
- `eval/`: Deterministic evaluation framework (145 boundary-tested cases).
- `samples/`: Sample bibliographies for live demos.
- `CITECHECK_SPEC.md`: Full architectural specification.
