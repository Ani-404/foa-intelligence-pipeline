# AI-Powered Funding Intelligence Pipeline

Minimal, readable pipeline for FOA ingestion, normalization, semantic tagging, export, and evaluation.

## Features
- Ingest FOAs from NSF/Grants.gov/generic sources (HTML, PDF, local files)
- Normalize to a single schema (JSON + CSV)
- Semantic tagging with controlled ontology:
  - rule-based tagging (default)
  - optional embedding similarity (`--use_embeddings`)
  - optional LLM-assisted tagging (`--use_llm` with `OPENAI_API_KEY`)
- Batch update workflow (via `main.py --input ...`)
- Evaluation script with precision/recall/F1

## Output Schema
`foa_id, title, agency, open_date, close_date, eligibility, program_description, award_range, source_url, source_type, tags, tagging_metadata`

## Setup
```bash
pip install -r requirements.txt
```

## Single FOA (screening task)
```bash
python main.py --url "https://example-foa-url" --out_dir ./out
```

## Local demo (network independent)
```bash
python main.py --url "file://data/sample_foa.html" --out_dir ./out --source nsf
```

## Real FOA examples (live websites)
Use these to test real-source behavior when the site is reachable from your network.

```bash
python main.py --url "https://new.nsf.gov/funding/opportunities/research-experiences-undergraduates-reu" --out_dir ./out --source nsf
python main.py --url "https://www.grants.gov/search-results-detail/353275" --out_dir ./out --source grantsgov
```

Expected top-quality behavior on reachable pages:
- `agency` correctly resolves to `NSF` or `Grants.gov`
- `title` and `program_description` are non-empty
- `foa_id` is extracted or generated deterministically
- Failures do not crash; fallback record is still exported

## Batch update workflow
```bash
python main.py --input data/foa_sources.txt --out_dir ./out --source auto
```

## Evaluation
```bash
python evaluate.py --eval_file data/eval_set.jsonl --out out/eval_metrics.json
```

## Known Limitations
- Some FOA pages block automated requests or load core content dynamically, which can reduce extraction quality.
- Date and section extraction still use heuristics; formatting differences across agencies can cause misses.
- Embedding and LLM tagging are optional and dependency/API dependent.

## Future Work
- Add source-specific parsers for stable NSF and Grants.gov templates (and NIH as the next source).
- Add retry/session handling plus optional browser rendering for anti-bot or JS-heavy pages.
- Expand evaluation with more real FOAs and per-source error analysis.

## Notes
- Pipeline always works in rule-based mode.
- Embedding/LLM modes are optional and fail-safe.
