import csv
import json
import os
from typing import Dict, List


CSV_FIELDS = [
    "foa_id",
    "title",
    "agency",
    "open_date",
    "close_date",
    "eligibility",
    "program_description",
    "award_range",
    "source_url",
    "source_type",
    "tags",
    "tagging_metadata",
]


def save_outputs(data: Dict, out_dir: str) -> None:
    json_path = os.path.join(out_dir, "foa.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    row = dict(data)
    row["tags"] = json.dumps(data.get("tags", {}), ensure_ascii=False)
    row["tagging_metadata"] = json.dumps(data.get("tagging_metadata", {}), ensure_ascii=False)

    csv_path = os.path.join(out_dir, "foa.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


def save_batch_outputs(records: List[Dict], out_dir: str, prefix: str = "foas") -> None:
    os.makedirs(out_dir, exist_ok=True)

    json_path = os.path.join(out_dir, f"{prefix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    csv_path = os.path.join(out_dir, f"{prefix}.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["tags"] = json.dumps(record.get("tags", {}), ensure_ascii=False)
            row["tagging_metadata"] = json.dumps(record.get("tagging_metadata", {}), ensure_ascii=False)
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})
