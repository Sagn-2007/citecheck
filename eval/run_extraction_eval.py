import json
import os
import sys
import time
import re
from rapidfuzz import fuzz

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from extract import extract_references, ReferenceExtractionError

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def compare_field(field_name: str, expected: any, actual: any) -> bool:
    if field_name == "year":
        return expected == actual
    elif field_name == "doi":
        if not expected and not actual: return True
        if not expected or not actual: return False
        return expected.lower().replace("https://doi.org/", "") == actual.lower().replace("https://doi.org/", "")
    elif field_name == "authors":
        if not expected and not actual: return True
        if not expected or not actual: return False
        exp_norm = {normalize_text(a) for a in expected}
        act_norm = {normalize_text(a) for a in actual}
        # In citations, authors are often represented as "Smith J" vs "J Smith", so we just check overlap ratio
        overlap = len(exp_norm.intersection(act_norm))
        return overlap / max(len(exp_norm), len(act_norm)) > 0.5
    elif field_name == "type":
        if not expected and not actual: return True
        if not expected or not actual: return False
        return expected == getattr(actual, "value", str(actual))
    else: # title, venue, raw
        if not expected and not actual: return True
        if not expected or not actual: return False
        return fuzz.ratio(normalize_text(expected), normalize_text(actual)) > 90

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    report_path = os.path.join(os.path.dirname(__file__), "extraction_results.md")
    
    if not api_key:
        print("GEMINI_API_KEY is not set. Live benchmark not executed. Please run with GEMINI_API_KEY.")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# CiteCheck Extraction Evaluation Report\n\n")
            f.write("⚠️ **Live benchmark skipped**: `GEMINI_API_KEY` was not set.\n\n")
            f.write("The evaluation infrastructure is validated via the deterministic tests in `backend/tests/test_extract.py`.\n")
        sys.exit(0)

    dataset_path = os.path.join(os.path.dirname(__file__), "extraction_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    field_metrics = {
        "authors": {"correct": 0, "incorrect": 0, "missing": 0},
        "title": {"correct": 0, "incorrect": 0, "missing": 0},
        "year": {"correct": 0, "incorrect": 0, "missing": 0},
        "venue": {"correct": 0, "incorrect": 0, "missing": 0},
        "doi": {"correct": 0, "incorrect": 0, "missing": 0},
        "type": {"correct": 0, "incorrect": 0, "missing": 0},
        "raw": {"correct": 0, "incorrect": 0, "missing": 0}
    }
    
    total_complete = 0
    total_references = 0
    failures = []
    
    start_time = time.time()
    
    for item in dataset:
        try:
            refs = extract_references(item["input"])
            expected_list = item["expected"] if isinstance(item["expected"], list) else [item["expected"]]
            
            if len(refs) != len(expected_list):
                failures.append({
                    "id": item["id"],
                    "category": item["category"],
                    "failure_type": "split/merge error",
                    "expected": len(expected_list),
                    "actual": len(refs),
                    "explanation": f"Expected {len(expected_list)} references but extracted {len(refs)}"
                })
                continue
                
            for ref, expected in zip(refs, expected_list):
                total_references += 1
                is_complete = True
                fail_reasons = []
                
                for field in ["authors", "title", "year", "venue", "doi", "type", "raw"]:
                    exp_val = expected.get(field)
                    act_val = getattr(ref, field)
                    
                    if exp_val is None and act_val is None:
                        # Correctly identified as missing/nullable
                        field_metrics[field]["correct"] += 1
                    elif exp_val is not None and (act_val is None or act_val == "" or act_val == []):
                        field_metrics[field]["missing"] += 1
                        is_complete = False
                        fail_reasons.append(f"{field} missing")
                    elif compare_field(field, exp_val, act_val):
                        field_metrics[field]["correct"] += 1
                    else:
                        field_metrics[field]["incorrect"] += 1
                        is_complete = False
                        fail_reasons.append(f"{field} mismatch: {exp_val} vs {act_val}")
                        
                if is_complete:
                    total_complete += 1
                else:
                    failures.append({
                        "id": item["id"],
                        "category": item["category"],
                        "failure_type": "field mismatch",
                        "expected": expected,
                        "actual": ref.model_dump(),
                        "explanation": ", ".join(fail_reasons)
                    })
                    
        except ReferenceExtractionError as e:
            failures.append({
                "id": item["id"],
                "category": item["category"],
                "failure_type": "extraction error",
                "expected": "valid json",
                "actual": "ReferenceExtractionError",
                "explanation": str(e)
            })
            
    total_time = time.time() - start_time
    avg_time = total_time / len(dataset) if dataset else 0
    
    # Generate Report
    report_path = os.path.join(os.path.dirname(__file__), "extraction_results.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# CiteCheck Extraction Evaluation Report\n\n")
        f.write("## Dataset Summary\n")
        f.write(f"- Total inputs: {len(dataset)}\n")
        f.write(f"- Total expected references: {total_references}\n\n")
        
        categories = {}
        for item in dataset:
            categories[item["category"]] = categories.get(item["category"], 0) + 1
        for cat, count in categories.items():
            f.write(f"- {cat}: {count}\n")
            
        f.write("\n## Overall Metrics\n")
        acc = (total_complete / total_references) * 100 if total_references else 0
        f.write(f"- Complete-reference accuracy: {acc:.2f}%\n")
        fail_rate = (len(failures) / len(dataset)) * 100 if dataset else 0
        f.write(f"- Extraction failure rate: {fail_rate:.2f}%\n")
        f.write(f"- Average processing time/input: {avg_time:.4f}s\n\n")
        
        f.write("## Field Metrics\n")
        f.write("| Field | Correct | Incorrect | Missing | Accuracy |\n")
        f.write("|-------|---------|-----------|---------|----------|\n")
        for field, counts in field_metrics.items():
            total = counts["correct"] + counts["incorrect"] + counts["missing"]
            field_acc = (counts["correct"] / total) * 100 if total else 0
            f.write(f"| {field} | {counts['correct']} | {counts['incorrect']} | {counts['missing']} | {field_acc:.2f}% |\n")
            
        f.write("\n## Architecture & Scoring\n")
        f.write("CiteCheck architecture: `Messy bibliography -> Gemini extraction -> Structured ExtractedReference -> Deterministic scholarly verification -> Final verdict`.\n")
        f.write("This benchmark ONLY measures the Gemini extraction quality. It does not verify the citation against scholarly databases. Extraction accuracy and verification accuracy are two entirely different metrics.\n")
        f.write("\nA complete-reference match requires ALL fields (authors, title, year, venue, doi, type, raw) to be extracted accurately.\n")
        
        f.write("\n## Failure Analysis\n")
        if not failures:
            f.write("No failures detected.\n")
        else:
            for fail in failures:
                f.write(f"### ID: {fail['id']} ({fail['category']}) - {fail['failure_type']}\n")
                f.write(f"- **Explanation**: {fail['explanation']}\n\n")

    print(f"Extraction evaluation complete. Output written to {report_path}")

if __name__ == "__main__":
    main()
