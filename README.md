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

## Batch update workflow
```bash
python main.py --input data/foa_sources.txt --out_dir ./out --source auto
```

## Evaluation
```bash
python evaluate.py --eval_file data/eval_set.jsonl --out out/eval_metrics.json
```

## Notes
- Pipeline always works in rule-based mode.
- Embedding/LLM modes are optional and fail-safe.
