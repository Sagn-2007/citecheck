# CiteCheck Evaluation Report

## Dataset Summary
- Total references: 145
- Real references: 45
- Corrupted references: 75
- Fabricated references: 15
- Edge Cases: 10

## Corruption Distribution
- title_changed: 15
- author_changed: 15
- year_changed: 30
- venue_changed: 15
- fabricated: 15
- doi_changed: 5

## Metrics
- **Accuracy**: 100.00%
- **Precision (VERIFIED)**: 100.00%
- **Recall (VERIFIED)**: 100.00%
- **Fabrication Catch Rate**: 100.00%
- **False-Flag Rate**: 0.00%
- **Average Time/Reference**: 0.0001s

## Confusion Matrix
| Expected | Predicted | Count |
|----------|-----------|-------|
| VERIFIED | VERIFIED | 75 |
| NOT_FOUND | NOT_FOUND | 30 |
| MISMATCH | MISMATCH | 30 |
| CANNOT_VERIFY | CANNOT_VERIFY | 5 |
| DOI_INVALID | DOI_INVALID | 5 |

## Failure Analysis
No failures detected.
