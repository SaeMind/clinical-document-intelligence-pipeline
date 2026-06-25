# Review Findings and Fixes

This file documents what was found during code review and what was changed, before this repository was pushed to GitHub. Keeping this record is intentional: a documented bug fix is a portfolio credibility signal, not something to hide.

## Critical: Hardcoded fake extraction data (fixed)

`src/extractor.py`'s demo-mode parsers for two of five document types did not actually parse the document text:

- `_parse_lab_results` returned a **fixed, hardcoded** `test_results` list (`Hemoglobin A1c`, `Creatinine`) regardless of what was actually in the PDF.
- `_parse_discharge` returned **fixed, hardcoded** `discharge_medications` (`Metformin`, `Lisinopril`) and `follow_up_appointments` (`Primary Care`, `7 days`) regardless of actual document content.

This meant the previously committed `outputs/run_20260625T142944Z/validation_report.json` showing a perfect 1.0 field accuracy / precision / recall / F1 across every document was partly meaningless: those specific fields would have shown the same "correct" values even if fed a completely different PDF, because they were never derived from the input.

**Fix:** both parsers now use regex extraction against the actual document text (`Test Results:` line for lab results; `Discharge Medications:` line for discharge summaries; `follow_up_appointments` is now heuristically derived from any follow-up instruction matching a "`<specialist> within <N> <unit>`" pattern, rather than a fixed constant).

**Verification:** the new parsing logic was tested against the real extracted PDF text and reproduces the ground-truth values correctly (one cosmetic exception: the source demo PDF for `lab_results_1.pdf` itself contains a truncated reference range, `"0.6-1.3 mg/d"` instead of `"...mg/dL"` — a pre-existing PDF-generation artifact, not a parsing bug; flagged here rather than silently patched over).

**New test coverage:** `tests/test_extractor.py` did not previously exist. Added, specifically using medication/lab-value names that differ from the old hardcoded defaults, so a regression back to hardcoded output would fail these tests even if it coincidentally matched the original demo PDFs.

## Stale committed output (removed)

`outputs/run_20260625T142944Z/` reflected the pre-fix, hardcoded-data behavior. Removed rather than left in place showing a now-inaccurate "perfect" score. Regenerate with `python src/main.py --batch data/sample_documents` before any demo or push.

## Not independently run-verified in this review pass

This review was conducted in a sandbox without network access, so `pydantic`, `anthropic`, and `pytest` could not be installed and the full pipeline (including Pydantic schema validation) could not be executed end-to-end here. The new regex parsing logic was verified in isolation (extracted and run directly against the real PDF text, outside the Pydantic-dependent module graph) and produces correct output. **Before pushing, run locally:**

```bash
pip install -r requirements.txt
pytest -q
python src/main.py --batch data/sample_documents
cat outputs/run_*/validation_report.json
```

Confirm `pytest -q` passes and the validation report's macro field accuracy is genuinely high (not just superficially 1.0 in a way that hides a problem) before treating this as resume-claimable per the standard credibility-gate process.

## Dependency pin risk (could not verify, flagging for your check)

`requirements.txt` pins `anthropic==0.57.1`. This sandbox has no network access, so this could not be checked against the real PyPI index. If that exact version does not exist, `pip install -r requirements.txt` — and therefore the GitHub Actions CI workflow — will fail immediately. Verify with `pip install anthropic==0.57.1` locally before pushing; if it fails, loosen to `anthropic>=0.57,<0.60` or update to the current released version.

