# GitHub Push Commands

```bash
cd ~/Downloads/portfolio-batch/document-intelligence-pipeline

# Regenerate outputs with the corrected extractor before committing
# (the previously committed run reflected a hardcoded-data bug since fixed --
# see CHANGELOG_REVIEW.md)
python src/main.py --batch data/sample_documents
pytest -q

git init
git add .
git commit -m "Structured clinical document intelligence pipeline: classification, schema-constrained extraction, Pydantic validation, gold-standard evaluation. Fixed hardcoded-output bug in lab results and discharge summary demo parsers; added missing extractor test coverage."
git branch -M main
gh repo create SaeMind/document-intelligence-pipeline --public --source=. --remote=origin --push
```

If the repo already exists:

```bash
git remote add origin https://github.com/SaeMind/document-intelligence-pipeline.git
git push -u origin main
```
