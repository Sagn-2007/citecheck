import csv
import json
import random

# Real Base References
BASE_REFERENCES = [
    {
        "id_prefix": "R01",
        "title": "A study of citation verification",
        "authors": ["Smith, J."],
        "year": 2020,
        "venue": "Journal of Testing",
        "doi": "10.1234/test.1",
        "type": "article",
        "source": "Crossref"
    },
    {
        "id_prefix": "R02",
        "title": "Deterministic matching engines",
        "authors": ["Doe, A.", "Lee, B."],
        "year": 2021,
        "venue": "IEEE Access",
        "doi": "10.1234/test.2",
        "type": "article",
        "source": "OpenAlex"
    },
    {
        "id_prefix": "R03",
        "title": "Machine learning for parsing citations",
        "authors": ["Wang, X.", "Zhang, Y.", "Liu, Q."],
        "year": 2019,
        "venue": "Conference on ML",
        "doi": "10.1234/test.3",
        "type": "conference",
        "source": "Semantic Scholar"
    },
    {
        "id_prefix": "R04",
        "title": "Deep learning in NLP",
        "authors": ["Jones, M."],
        "year": 2022,
        "venue": "NLP Transactions",
        "doi": None,
        "type": "article",
        "source": "Crossref"
    },
    {
        "id_prefix": "R05",
        "title": "A survey of large language models",
        "authors": ["Brown, C.", "White, D."],
        "year": 2023,
        "venue": "AI Review",
        "doi": "10.5678/ai.2023",
        "type": "article",
        "source": "OpenAlex"
    }
]

# We will generate more base references by duplicating and perturbing safely
more_bases = []
for i in range(6, 16):
    ref = BASE_REFERENCES[i % 5].copy()
    ref["id_prefix"] = f"R{i:02d}"
    ref["title"] = ref["title"] + f" Part {i}"
    if ref["doi"]:
        ref["doi"] = ref["doi"] + str(i)
    more_bases.append(ref)

ALL_BASES = BASE_REFERENCES + more_bases

# MOCK DB contains all real baselines
mock_db = []
for ref in ALL_BASES:
    mock_db.append({
        "title": ref["title"],
        "authors": ref["authors"],
        "year": ref["year"],
        "venue": ref["venue"],
        "doi": ref["doi"],
        "source": ref["source"]
    })

# We'll build the dataset
dataset = []
random.seed(42)

def make_raw(ref):
    auth_str = ", ".join(ref["authors"])
    year_str = f"({ref['year']})" if ref['year'] else ""
    venue_str = ref['venue'] if ref['venue'] else ""
    doi_str = ref['doi'] if ref['doi'] else ""
    parts = [p for p in [auth_str, year_str, ref['title'], venue_str, doi_str] if p]
    return ". ".join(parts) + "."

def add_record(id_val, ref, expected_label, category, corruption_type, notes):
    dataset.append({
        "id": id_val,
        "raw_reference": make_raw(ref),
        "title": ref["title"],
        "authors": "|".join(ref["authors"]),
        "year": ref["year"],
        "venue": ref.get("venue", ""),
        "doi": ref.get("doi", ""),
        "type": ref["type"],
        "expected_label": expected_label,
        "category": category,
        "corruption_type": corruption_type,
        "notes": notes
    })

current_id = 1

# 1. Real references (No corruption) -> ~45 cases
for base in ALL_BASES:
    # 1.1 Exact match
    add_record(current_id, base, "VERIFIED", "real", "none", "Exact match real reference")
    current_id += 1
    
    # 1.2 Minor title typo (should verify)
    ref_typo = base.copy()
    ref_typo["title"] = ref_typo["title"][:-1] + "x"
    add_record(current_id, ref_typo, "VERIFIED", "real", "none", "Minor typo in title")
    current_id += 1
    
    # 1.3 Missing venue (should verify)
    ref_no_venue = base.copy()
    ref_no_venue["venue"] = None
    add_record(current_id, ref_no_venue, "VERIFIED", "real", "none", "Missing venue but other fields match")
    current_id += 1

# 2. Corrupted References -> ~40 cases
for base in ALL_BASES:
    # 2.1 Major title change (should NOT_FOUND)
    ref_bad_title = base.copy()
    ref_bad_title["title"] = "A completely unrelated study about something else entirely"
    add_record(current_id, ref_bad_title, "NOT_FOUND", "corrupted", "title_changed", "Title heavily changed")
    current_id += 1
    
    # 2.2 First author change (should MISMATCH)
    ref_bad_author = base.copy()
    ref_bad_author["authors"] = ["Fakeauthor, X."] + base["authors"][1:]
    add_record(current_id, ref_bad_author, "MISMATCH", "corrupted", "author_changed", "First author mismatch")
    current_id += 1
    
    # 2.3 Year changed by 2+ (should MISMATCH)
    ref_bad_year = base.copy()
    if ref_bad_year["year"]:
        ref_bad_year["year"] += 5
        add_record(current_id, ref_bad_year, "MISMATCH", "corrupted", "year_changed", "Year mismatch > 1")
        current_id += 1
        
    # 2.4 Year changed by 1 (should VERIFIED)
    ref_off_year = base.copy()
    if ref_off_year["year"]:
        ref_off_year["year"] += 1
        add_record(current_id, ref_off_year, "VERIFIED", "corrupted", "year_changed", "Year mismatch = 1, allowed")
        current_id += 1
        
    # 2.5 Venue changed (should VERIFIED since engine only checks Title/Author/Year strictly)
    ref_bad_venue = base.copy()
    ref_bad_venue["venue"] = "Completely Wrong Journal"
    add_record(current_id, ref_bad_venue, "VERIFIED", "corrupted", "venue_changed", "Venue changed but matching engine ignores it for verification")
    current_id += 1
    
# 3. Fabricated References -> ~15 cases
for i in range(15):
    fab = {
        "title": f"Hallucinated AI Paper {i}",
        "authors": ["Fake, A."],
        "year": 2025,
        "venue": "Journal of Imaginary Findings",
        "doi": None,
        "type": "article"
    }
    add_record(current_id, fab, "NOT_FOUND", "fabricated", "fabricated", "Completely fabricated")
    current_id += 1
    
# 4. Edge Cases -> ~10 cases
for i in range(5):
    # Web reference
    edge1 = {
        "title": f"Web Article {i}",
        "authors": ["Blogger, B."],
        "year": 2020,
        "venue": f"http://example.com/{i}",
        "doi": None,
        "type": "web"
    }
    add_record(current_id, edge1, "CANNOT_VERIFY", "edge_case", "none", "Web reference cannot be verified")
    current_id += 1
    
    # Bad DOI
    edge2 = base.copy()
    edge2["doi"] = "invalid_doi_format_123"
    add_record(current_id, edge2, "DOI_INVALID", "edge_case", "doi_changed", "Invalid DOI string")
    current_id += 1

# Write dataset
with open('eval/dataset.csv', 'w', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        "id", "raw_reference", "title", "authors", "year", 
        "venue", "doi", "type", "expected_label", "category", "corruption_type", "notes"
    ])
    writer.writeheader()
    for row in dataset:
        writer.writerow(row)

# Write mock db
with open('eval/mock_db.json', 'w', encoding='utf-8') as f:
    json.dump(mock_db, f, indent=2)

print(f"Generated {len(dataset)} evaluation records.")
