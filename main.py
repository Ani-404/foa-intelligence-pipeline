import argparse
import logging
import os

from extractor import extract_foa
from tagger import tag_foa
from utils import save_batch_outputs, save_outputs

logging.basicConfig(level=logging.INFO, format="%(message)s")


def process_url(url, source, use_embeddings, use_llm):
    record = extract_foa(url=url, source_hint=source)
    tag_payload = tag_foa(
        foa_record=record,
        use_embeddings=use_embeddings,
        use_llm=use_llm,
    )
    record["tags"] = tag_payload["tags"]
    record["tagging_metadata"] = tag_payload["metadata"]
    return record


def run_single(url, out_dir, source, use_embeddings, use_llm):
    logging.info("Processing single FOA")
    record = process_url(url, source, use_embeddings, use_llm)
    save_outputs(record, out_dir)
    logging.info("Saved foa.json and foa.csv")


def run_batch(input_file, out_dir, source, use_embeddings, use_llm):
    logging.info(f"Processing batch input: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    records = []
    for idx, url in enumerate(urls, start=1):
        logging.info(f"[{idx}/{len(urls)}] {url}")
        records.append(process_url(url, source, use_embeddings, use_llm))

    save_batch_outputs(records, out_dir=out_dir, prefix="foas")
    logging.info("Saved foas.json and foas.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FOA ingestion + semantic tagging pipeline")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--url", help="Single FOA URL/path")
    mode.add_argument("--input", help="Batch file: one URL/path per line")

    parser.add_argument("--out_dir", default="./out", help="Output directory")
    parser.add_argument(
        "--source",
        default="auto",
        choices=["auto", "nsf", "grantsgov", "generic"],
        help="Source hint",
    )
    parser.add_argument("--use_embeddings", action="store_true")
    parser.add_argument("--use_llm", action="store_true")

    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    if args.url:
        run_single(args.url, args.out_dir, args.source, args.use_embeddings, args.use_llm)
    else:
        run_batch(args.input, args.out_dir, args.source, args.use_embeddings, args.use_llm)
