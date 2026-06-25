# Outputs Directory

Pipeline runs write timestamped output folders here (`run_<UTC timestamp>/`), each containing:

- `extracted_data.jsonl` — one structured extraction record per processed PDF
- `validation_report.json` — schema pass rates and gold-standard field-level accuracy/precision/recall/F1
- `error_log.json` — any per-document processing failures

Run folders are excluded from version control (`.gitignore`) except this README, so the repository stays clean across repeated runs.

**Before pushing or demoing:** generate a fresh run rather than relying on a previously committed one, since output content reflects whatever extractor logic is current at run time:

```bash
python src/main.py --batch data/sample_documents
cat outputs/run_*/validation_report.json
```
