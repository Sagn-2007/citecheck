import os
import sys
import csv
import time
from typing import List, Dict, Any

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from models import ExtractedReference, Verdict, ScholarlyCandidate
import verify_one
import extract
import lookup

import json

# --- Deterministic Mocks for Scholarly APIs ---
MOCK_DATABASE = []
mock_db_path = os.path.join(os.path.dirname(__file__), "mock_db.json")
if os.path.exists(mock_db_path):
    with open(mock_db_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for item in data:
            MOCK_DATABASE.append(ScholarlyCandidate(**item))

from rapidfuzz import fuzz

async def mock_lookup_by_doi(doi: str) -> ScholarlyCandidate | None:
    for cand in MOCK_DATABASE:
        if cand.doi and cand.doi.lower() == doi.lower():
            return cand
    return None

async def mock_search_crossref(title: str, author: str) -> List[ScholarlyCandidate]:
    return [c for c in MOCK_DATABASE if c.source == "Crossref" and fuzz.ratio(c.title.lower(), title.lower()) > 60]

async def mock_search_openalex(title: str) -> List[ScholarlyCandidate]:
    return [c for c in MOCK_DATABASE if c.source == "OpenAlex" and fuzz.ratio(c.title.lower(), title.lower()) > 60]

async def mock_search_semantic_scholar(title: str) -> List[ScholarlyCandidate]:
    return [c for c in MOCK_DATABASE if c.source == "Semantic Scholar" and fuzz.ratio(c.title.lower(), title.lower()) > 60]

from unittest.mock import patch
import asyncio

# Apply Mocks via patch
patcher_doi = patch('verify_one.lookup_by_doi', new=mock_lookup_by_doi)
patcher_bib = patch('verify_one.search_by_bibliographic', new=mock_search_crossref)
patcher_oa = patch('verify_one.search_openalex', new=mock_search_openalex)
patcher_s2 = patch('verify_one.search_semantic_scholar', new=mock_search_semantic_scholar)
# Also prevent caching side-effects during eval by mocking the cache
patcher_db = patch.dict('os.environ', {"CITECHECK_CACHE_DB": ":memory:"})

patcher_doi.start()
patcher_bib.start()
patcher_oa.start()
patcher_s2.start()
patcher_db.start()

# --- Dataset and Metric definitions ---

class EvaluationMetrics:
    def __init__(self):
        self.total = 0
        self.correct = 0
        self.fabricated = 0
        self.fabricated_caught = 0
        self.legitimate = 0
        self.false_flags = 0
        self.processing_times = []
        self.confusion_matrix: Dict[str, Dict[str, int]] = {}
        self.failures = []
        self.categories = {"real": 0, "corrupted": 0, "fabricated": 0, "edge_case": 0}
        self.corruptions = {}

    def record(self, expected: str, predicted: str, duration: float, item: Dict[str, Any], result: Any):
        self.total += 1
        self.processing_times.append(duration)
        
        cat = item.get("category", "unknown")
        if cat in self.categories:
            self.categories[cat] += 1
            
        ctype = item.get("corruption_type", "none")
        if ctype != "none":
            self.corruptions[ctype] = self.corruptions.get(ctype, 0) + 1
        
        if expected not in self.confusion_matrix:
            self.confusion_matrix[expected] = {}
        self.confusion_matrix[expected][predicted] = self.confusion_matrix[expected].get(predicted, 0) + 1

        if expected == predicted:
            self.correct += 1
        else:
            self.failures.append({
                "id": item["id"],
                "category": cat,
                "corruption_type": ctype,
                "expected": expected,
                "predicted": predicted,
                "metadata": item["raw_reference"],
                "notes": item["notes"],
                "differences": [d.model_dump() for d in result.field_differences] if result.field_differences else []
            })

        # Fabrication catch rate
        if cat == "fabricated":
            self.fabricated += 1
            if predicted == "NOT_FOUND":
                self.fabricated_caught += 1

        # False flag rate (Real references expected to be VERIFIED)
        if cat == "real" and expected == "VERIFIED":
            self.legitimate += 1
            if predicted != "VERIFIED":
                self.false_flags += 1

def run_evaluation(dataset_path: str):
    metrics = EvaluationMetrics()
    
    with open(dataset_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            authors = [a.strip() for a in row["authors"].split("|")] if row["authors"] else []
            year = int(row["year"]) if row["year"] else None
            doi = row["doi"] if row["doi"] else None
            venue = row["venue"] if row["venue"] else None
            
            ext_ref = ExtractedReference(
                raw=row["raw_reference"],
                title=row["title"],
                authors=authors,
                year=year,
                venue=venue,
                doi=doi,
                type=row["type"]
            )
            
            import asyncio
            start_time = time.time()
            result = asyncio.run(verify_one.verify_reference(ext_ref))
            duration = time.time() - start_time
            
            metrics.record(row["expected_label"], result.verdict.value, duration, row, result)
            
    return metrics

def generate_report(metrics: EvaluationMetrics, output_path: str):
    accuracy = (metrics.correct / metrics.total) * 100 if metrics.total else 0
    fab_catch = (metrics.fabricated_caught / metrics.fabricated) * 100 if metrics.fabricated else 0
    false_flag = (metrics.false_flags / metrics.legitimate) * 100 if metrics.legitimate else 0
    avg_time = sum(metrics.processing_times) / len(metrics.processing_times) if metrics.processing_times else 0

    # Calculate Precision and Recall for VERIFIED class
    tp = metrics.confusion_matrix.get("VERIFIED", {}).get("VERIFIED", 0)
    fp = sum(preds.get("VERIFIED", 0) for exp, preds in metrics.confusion_matrix.items() if exp != "VERIFIED")
    fn = sum(count for pred, count in metrics.confusion_matrix.get("VERIFIED", {}).items() if pred != "VERIFIED")
    
    precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0
    recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# CiteCheck Evaluation Report\n\n")
        f.write("## Dataset Summary\n")
        f.write(f"- Total references: {metrics.total}\n")
        f.write(f"- Real references: {metrics.categories['real']}\n")
        f.write(f"- Corrupted references: {metrics.categories['corrupted']}\n")
        f.write(f"- Fabricated references: {metrics.categories['fabricated']}\n")
        f.write(f"- Edge Cases: {metrics.categories['edge_case']}\n")
        
        f.write("\n## Corruption Distribution\n")
        for ctype, count in metrics.corruptions.items():
            f.write(f"- {ctype}: {count}\n")
            
        f.write("\n## Metrics\n")
        f.write(f"- **Accuracy**: {accuracy:.2f}%\n")
        f.write(f"- **Precision (VERIFIED)**: {precision:.2f}%\n")
        f.write(f"- **Recall (VERIFIED)**: {recall:.2f}%\n")
        f.write(f"- **Fabrication Catch Rate**: {fab_catch:.2f}%\n")
        f.write(f"- **False-Flag Rate**: {false_flag:.2f}%\n")
        f.write(f"- **Average Time/Reference**: {avg_time:.4f}s\n")
        
        f.write("\n## Confusion Matrix\n")
        f.write("| Expected | Predicted | Count |\n")
        f.write("|----------|-----------|-------|\n")
        for exp, preds in metrics.confusion_matrix.items():
            for pred, count in preds.items():
                f.write(f"| {exp} | {pred} | {count} |\n")
                
        f.write("\n## Failure Analysis\n")
        if not metrics.failures:
            f.write("No failures detected.\n")
        else:
            for fail in metrics.failures:
                f.write(f"### ID: {fail['id']} ({fail['category']} - {fail['corruption_type']})\n")
                f.write(f"- **Expected**: {fail['expected']}\n")
                f.write(f"- **Predicted**: {fail['predicted']}\n")
                f.write(f"- **Raw Reference**: {fail['metadata']}\n")
                f.write(f"- **Notes**: {fail['notes']}\n")
                if fail['differences']:
                    f.write("- **Field Differences**:\n")
                    for diff in fail['differences']:
                        f.write(f"  - {diff['field_name']}: {diff['submitted']} vs {diff['matched']}\n")
                f.write("\n")

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    dataset_csv = os.path.join(base_dir, "dataset.csv")
    output_md = os.path.join(base_dir, "results.md")
    
    print(f"Loading dataset from {dataset_csv}")
    metrics = run_evaluation(dataset_csv)
    print("Evaluation completed. Generating report...")
    generate_report(metrics, output_md)
    print(f"Report written to {output_md}")
