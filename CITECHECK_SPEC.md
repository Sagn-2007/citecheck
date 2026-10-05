# CiteCheck — Citation Verifier for AI-Written Reports

**Event:** INNOV12 — Undergraduate Innovation & Product Challenge (IEM)
**Track:** Cyber & Digital Trust (also fits AI & GenAI / Responsible AI)
**Submission deadline:** 7 October 2026 · **Finale:** 12 October 2026, 2:00–5:00 PM

> *Working name: CiteCheck. Rename freely.*

---

## 1. The Problem

LLMs write fluent, confident bibliographies. A significant share of the references they produce are **fabricated** (the paper does not exist) or **corrupted** (the paper exists, but the authors, year, venue, or DOI are wrong). Students, researchers, and journalists now paste AI-assisted text into reports, theses, and papers, and checking every reference by hand takes several minutes each.

Consequences:
- Fake citations in submitted academic work (integrity and credibility damage)
- Wasted time hunting for papers that don't exist
- Erosion of trust in AI-assisted writing

**Core idea:** the LLM may *propose* references, but a **deterministic checker against real scholarly databases decides** whether they are real. Correctness comes from lookups and matching, not from a model's opinion.

---

## 2. What We Build

A web app where the user pastes a bibliography (or uploads a PDF/DOCX) and receives a **per-reference verdict report**:

| Verdict | Meaning |
|---|---|
| ✅ **Verified** | A matching real paper exists; title, first author, and year agree |
| ⚠️ **Mismatch** | A real paper matches the title, but authors, year, or venue differ (the "half-hallucinated" case) |
| ❌ **Not found** | No candidate above threshold in any database; likely fabricated |
| 🔗 **DOI invalid** | DOI doesn't resolve, or resolves to a different paper |
| ❔ **Cannot verify** | Book, thesis, website, or non-indexed source; not marked fake |

Each row shows the **closest real match** and **exactly which fields differ**, plus a document-level **Reliability Score** and a CSV export.

---

## 3. Architecture

```
┌────────────┐   text/PDF   ┌──────────────┐   JSON refs   ┌──────────────────┐
│  Frontend  │ ───────────▶ │  FastAPI     │ ────────────▶ │  Gemini (extract │
│  React     │              │  backend     │ ◀──────────── │  only, JSON mode)│
└────────────┘              └──────┬───────┘               └──────────────────┘
      ▲                            │ per reference
      │ report JSON                ▼
      │                    ┌───────────────┐   ┌─────────────┐
      └─────────────────── │ Match engine  │◀─▶│ SQLite cache│
                           │ (rapidfuzz +  │   └─────────────┘
                           │  rules)       │
                           └──────┬────────┘
                                  ▼
                  Crossref · OpenAlex · Semantic Scholar APIs
```

**Design principle:** the LLM is used in exactly one place (turning messy text into structured fields). Every verdict is produced by deterministic code.

---

## 4. Pipeline in Detail

### Step 1 — Extract references
- Input: pasted text, PDF, or DOCX.
- PDF/DOCX → plain text (`pdfplumber` / `python-docx`), then isolate the references section (heading match on "References" / "Bibliography" / "Works Cited").
- Gemini with a JSON schema returns a list of:

```json
{
  "raw": "original reference string",
  "authors": ["Surname, Initials", "..."],
  "title": "string",
  "year": 2021,
  "venue": "journal or conference",
  "doi": "10.xxxx/xxxx or null",
  "type": "article | conference | book | web | other"
}
```
- Keep the `raw` string so the report can always show what the user pasted.
- Set temperature to 0 and validate output with Pydantic; retry once on invalid JSON.

### Step 2 — Look up candidates
| Case | Action |
|---|---|
| DOI present | `GET https://api.crossref.org/works/{doi}`; compare returned title and authors |
| No DOI | Crossref: `GET /works?query.bibliographic=<title + first author>&rows=3` |
| Crossref weak | OpenAlex: `GET https://api.openalex.org/works?search=<title>&per-page=3` |
| Still weak | Semantic Scholar: `GET https://api.semanticscholar.org/graph/v1/paper/search?query=<title>&limit=3&fields=title,authors,year,venue,externalIds` |

Practicalities:
- Add a `mailto=` parameter to Crossref and OpenAlex requests (their "polite pool" gives better rate limits).
- Query databases **in order and stop early** once a strong match is found.
- Cache every response in SQLite keyed by normalized query, so reruns and the live demo are fast.
- Run lookups concurrently with `asyncio` + `httpx`, with a small semaphore to respect rate limits.

### Step 3 — Compare
Normalize first: lowercase, strip punctuation and LaTeX/HTML tags, collapse whitespace, remove stopwords for title comparison.

| Field | Method |
|---|---|
| Title | `rapidfuzz.fuzz.token_set_ratio` and `fuzz.ratio`, take the stronger signal |
| Authors | Compare **surnames** only (set overlap, order-insensitive for the first 3); tolerate initials/transliteration |
| Year | Exact match, or ±1 allowed for preprint vs. published |
| Venue | Soft match (fuzzy), low weight; used only as supporting evidence |

### Step 4 — Verdict (deterministic rules)

```python
def verdict(title_sim, first_author_ok, author_overlap, year_ok, doi_status, found):
    if doi_status == "invalid":
        return "DOI_INVALID"
    if not found or title_sim < 70:
        return "NOT_FOUND"            # or CANNOT_VERIFY if type in {book, web, thesis}
    if title_sim >= 90 and first_author_ok and year_ok:
        return "VERIFIED"
    return "MISMATCH"                  # real paper, wrong metadata
```

Thresholds (90 / 70) are **starting points**; tune them on your labeled dataset and report the final values.

### Step 5 — Report
- Table with color-coded verdicts, expandable rows showing *your reference vs. closest real match*, field-level diff highlighting (e.g., authors differ, year 2019 vs 2021).
- Summary card: counts per verdict + **Reliability Score** = verified ÷ total checkable references.
- CSV/JSON export; optional "corrected reference" suggestion built from the matched record (for Mismatch only).

---

## 5. Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.11, FastAPI, `httpx`, `rapidfuzz`, `pydantic` |
| LLM | Gemini 3.1 Pro (extraction only, JSON mode, temperature 0) |
| File parsing | `pdfplumber`, `python-docx` |
| Data sources | Crossref, OpenAlex, Semantic Scholar (all free) |
| Cache | SQLite |
| Frontend | React (Vite) + Tailwind, or plain HTML + fetch if time is short |
| Deployment | Run locally for the video; optionally Render/Vercel |
| Cost | Near zero (free APIs + low Gemini usage) |

### Suggested repo layout

```
citecheck/
├── backend/
│   ├── main.py            # FastAPI routes
│   ├── extract.py         # Gemini extraction + schema validation
│   ├── lookup.py          # Crossref / OpenAlex / S2 clients + cache
│   ├── match.py           # normalization, similarity, verdict rules
│   ├── models.py          # Pydantic schemas
│   └── cache.db
├── frontend/
│   └── src/ (UploadPanel, ReportTable, DiffView, SummaryCard)
├── eval/
│   ├── dataset.csv        # labeled references
│   ├── run_eval.py        # precision / recall / false-flag rate
│   └── results.md
├── samples/               # demo bibliographies
└── README.md
```

---

## 6. Evaluation Plan (Your Headline Numbers)

Strong entries show measured results. Build this dataset **starting today**: labeling is the time sink.

**Dataset construction**
1. Ask an LLM to write ~50 short reference lists on varied topics (ML, medicine, economics, physics). This yields natural hallucinations.
2. Manually label each reference as **Real / Fabricated / Corrupted** by checking Google Scholar/DOI. Split the labeling across all four members; aim for 100–150 references.
3. Add **synthetic corruptions** from known-real references: swap authors, change the year, alter a title word, break a DOI.
4. Include 15–20 legitimate books/websites to measure false flags.

**Metrics to report**
| Metric | Definition |
|---|---|
| Fabrication catch rate (recall) | Fabricated refs flagged Not found / Mismatch ÷ all fabricated |
| Precision | Flagged refs that were truly bad ÷ all flagged refs |
| False-flag rate | Real refs wrongly flagged ÷ all real refs |
| Time per reference | Mean with cold cache and warm cache |
| LLM fabrication rate | % of raw LLM references that were fabricated or corrupted (the shareable stat) |

**Baseline comparison (strong differentiator):** ask Gemini directly "Is this reference real?" on the same dataset and compare against CiteCheck. Show where the LLM confidently approves fakes.

---

## 7. Known Limitations (State Them Honestly)

- Books, theses, websites, patents, and some conference papers are poorly indexed → handled by the **Cannot verify** bucket, never labeled "fake".
- Non-English or transliterated titles reduce match quality.
- Very recent preprints may not be indexed yet.
- The tool verifies that a reference **exists and its metadata is correct**, not that the paper **supports the claim** it is cited for.

---

## 8. What Makes It Unique

- **Deterministic verification:** the LLM never decides truth, so it cannot be fooled by its own fluency.
- **Field-level explanations:** not just "fake", but "real paper found, authors differ, year 2019 vs 2021".
- **Measured against an LLM-judge baseline,** with published precision/recall.
- **Direct fit to Responsible AI:** addresses a documented failure mode of generative AI.

---

## 9. Target Users and Real-World Application

| User | Use |
|---|---|
| Undergraduate / postgraduate students | Check AI-assisted assignments and theses before submission |
| Research supervisors, reviewers | Screen submitted bibliographies quickly |
| Librarians, journal editors | Integrity checks at scale |
| Journalists, analysts | Verify sources in AI-assisted drafts |

Pilot idea for the finale: run it on real bibliographies from IEM students (with permission) and report how many contained at least one bad reference.

---

## 10. Future Scope

- **Claim-to-source checking:** verify that the cited paper actually supports the sentence it is attached to
- Browser extension and "paste from ChatGPT" mode
- Word/Google Docs add-in
- Integration with university LMS or plagiarism-check workflows
- Retraction checking (via Crossref/Retraction Watch data)
- Support for more sources (PubMed, arXiv, DBLP, IEEE) and Indian regional databases

---

## 11. 48-Hour Plan

| When | Goal |
|---|---|
| **Oct 5 (today)** | Lock team (4 members, ≥1 female), set up repo, extraction + Crossref lookup + match rules working end-to-end on a text file via CLI. **Start dataset labeling immediately** |
| **Oct 6** | Add OpenAlex/S2 fallback, caching, React report UI, PDF upload. Run evaluation, tune thresholds, fix failure cases |
| **Oct 7 AM** | Freeze features. Record demo video. Finalize documentation with real numbers |
| **Oct 7 (before deadline)** | Submit documentation + MP4. Submit early, not at the last hour |

### Role split

| Member | Responsibility |
|---|---|
| 1 | Backend core: extraction, lookups, matching, verdict logic |
| 2 | Frontend: upload, report table, diff view, summary card |
| 3 | Dataset creation/labeling, `run_eval.py`, metrics and baseline comparison |
| 4 | Documentation, demo script and video, edge cases, caching, deployment |

*Everyone labels references on Day 1. The leader (single point of contact) coordinates submission.*

---

## 12. Demo Video Script (3–4 minutes)

Follows the required flow: **Problem → Solution → Product → Working Demo → Key Innovation**

| Time | Content |
|---|---|
| 0:00–0:30 | **Problem:** show an LLM-written bibliography; pick one reference and show it doesn't exist on Google Scholar |
| 0:30–1:00 | **Solution:** one-line pitch + the pipeline diagram |
| 1:00–2:30 | **Live demo:** paste the bibliography → watch each reference resolve → show a Verified row, a Mismatch row (diff highlighting), and a Not found row. Upload a PDF to show batch mode |
| 2:30–3:15 | **Key innovation:** deterministic checking vs. asking an LLM; show the baseline comparison chart |
| 3:15–3:45 | **Results:** precision, recall, false-flag rate, fabrication stat from your dataset |
| 3:45–4:00 | Limitations, future scope, team |

Tips: use real screen recording, not slides; keep a pre-warmed cache so the demo is instant; show one honest failure case and how it's handled ("Cannot verify" bucket).

---

## 13. Documentation Draft Mapped to Required Sections

| Required section | Draft content |
|---|---|
| **Project Title** | CiteCheck — Citation Verifier for AI-Written Reports |
| **Selected Challenge Track** | Cyber & Digital Trust |
| **Problem Statement** | Section 1 above, with your measured fabrication rate |
| **What You Built** | Web app that verifies bibliography entries against Crossref/OpenAlex/Semantic Scholar and reports per-reference verdicts |
| **How It Works** | Sections 3–4 (pipeline diagram + five steps) |
| **Key Technologies Used** | Section 5 |
| **What Makes It Unique?** | Section 8 |
| **Target Users / Customers** | Section 9 |
| **Real-World Application** | Academic integrity checks, editorial screening, journalism; pilot results |
| **Innovation & Differentiating Features** | Deterministic verdicts, field-level diffs, LLM-judge baseline, reliability score |
| **Approximate Cost** | ~₹0 infrastructure (free APIs, local hosting); Gemini usage minimal |
| **Current Development Status** | Working prototype (update at submission) |
| **Future Scope** | Section 10 |
| **Team Contributions** | Section 11 role table, filled in with real names |

---

## 14. Prompt for the Coding CLI (Scaffolding)

```
Build a FastAPI backend and React frontend called "citecheck".

Goal: verify bibliography entries against real scholarly databases.

Backend:
1. POST /verify accepts {text: string}. Use Gemini (JSON mode, temperature 0) to
   extract references into this Pydantic schema: raw, authors[], title, year,
   venue, doi, type.
2. For each reference, look up candidates: DOI -> Crossref /works/{doi};
   otherwise Crossref query.bibliographic (rows=3), then OpenAlex search, then
   Semantic Scholar search as fallback. Use httpx async, a mailto param, and a
   SQLite cache keyed by normalized query.
3. Compare with rapidfuzz (title token_set_ratio), author surname overlap, and
   year (±1 allowed).
4. Assign verdicts in plain Python rules (no LLM): VERIFIED, MISMATCH,
   NOT_FOUND, DOI_INVALID, CANNOT_VERIFY. Return the closest candidate and a
   per-field diff.
5. Add POST /verify-file for PDF/DOCX (pdfplumber, python-docx).

Frontend: upload/paste panel, color-coded results table with expandable diff
view, summary card with reliability score, CSV export.

Also create eval/run_eval.py that reads eval/dataset.csv (raw, label) and
prints precision, recall, false-flag rate, and mean time per reference.
Keep the code simple; do not add features beyond this spec.
```

---

## 15. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| API rate limits or downtime during the demo | SQLite cache, pre-warmed demo inputs, polite-pool `mailto`, local fallback fixtures |
| False flags on books/web sources | "Cannot verify" bucket; report the false-flag rate openly |
| Labeling takes too long | Start Day 1, split across 4 members, cap dataset at ~120 references |
| Gemini extraction errors on messy formats | Pydantic validation, one retry, keep `raw` string, test across APA/IEEE/MLA styles |
| Scope creep from the coding agent | Freeze scope at end of Day 1; review every change |
