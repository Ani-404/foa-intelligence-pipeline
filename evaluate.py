import argparse
import json
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from tagger import tag_foa


def _normalize_pairs(tags: Dict[str, List[str]]) -> Set[Tuple[str, str]]:
    pairs = set()
    for category, values in tags.items():
        for tag in values:
            if tag != "unspecified":
                pairs.add((category, tag))
    return pairs


def _safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0


def evaluate(eval_file: str, use_embeddings: bool, use_llm: bool) -> Dict:
    total_tp = 0
    total_fp = 0
    total_fn = 0

    per_category = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    with open(eval_file, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    for row in rows:
        foa = {
            "title": row.get("title", ""),
            "eligibility": row.get("eligibility", ""),
            "program_description": row.get("program_description", ""),
        }

        pred = tag_foa(foa, use_embeddings=use_embeddings, use_llm=use_llm)["tags"]
        gold = row["gold_tags"]

        pred_pairs = _normalize_pairs(pred)
        gold_pairs = _normalize_pairs(gold)

        tp = len(pred_pairs & gold_pairs)
        fp = len(pred_pairs - gold_pairs)
        fn = len(gold_pairs - pred_pairs)

        total_tp += tp
        total_fp += fp
        total_fn += fn

        for category in set(list(pred.keys()) + list(gold.keys())):
            p = set((category, t) for t in pred.get(category, []) if t != "unspecified")
            g = set((category, t) for t in gold.get(category, []) if t != "unspecified")
            per_category[category]["tp"] += len(p & g)
            per_category[category]["fp"] += len(p - g)
            per_category[category]["fn"] += len(g - p)

    precision = _safe_div(total_tp, total_tp + total_fp)
    recall = _safe_div(total_tp, total_tp + total_fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    category_metrics = {}
    for category, counts in per_category.items():
        p = _safe_div(counts["tp"], counts["tp"] + counts["fp"])
        r = _safe_div(counts["tp"], counts["tp"] + counts["fn"])
        category_metrics[category] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(_safe_div(2 * p * r, p + r), 4),
            "tp": counts["tp"],
            "fp": counts["fp"],
            "fn": counts["fn"],
        }

    return {
        "num_examples": len(rows),
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
        "counts": {"tp": total_tp, "fp": total_fp, "fn": total_fn},
        "per_category": category_metrics,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate semantic tagging consistency")
    parser.add_argument("--eval_file", default="data/eval_set.jsonl")
    parser.add_argument("--out", default="out/eval_metrics.json")
    parser.add_argument("--use_embeddings", action="store_true")
    parser.add_argument("--use_llm", action="store_true")

    args = parser.parse_args()

    metrics = evaluate(
        eval_file=args.eval_file,
        use_embeddings=args.use_embeddings,
        use_llm=args.use_llm,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(json.dumps(metrics, indent=2))
