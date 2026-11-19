"""Local benchmark, extractive CV preview, and optional LoRA. See docs/EVIDENCE_PAIRING.md."""
import argparse
import hashlib
import json
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.evidence_pairing import (LABELS, checked, lexical_answer, preview, retrieval,
                                   strict_json, validate_packet)
from core.training_split_audit import audit_splits

FIXTURE = ROOT / "examples/fictional/evidence-pairing.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_cases(path):
    data = strict_json(path.read_text(encoding="utf-8"))
    if data.get("schema") != "evidence-benchmark-1" or data.get("provenance") != "synthetic_qa":
        raise ValueError("This pilot accepts declared fictional QA cases only")
    audit_rows = []
    for case in data["cases"]:
        packet = case["packet"]
        facts = validate_packet(packet)
        reqs = packet["requirements"]
        if set(case["gold"]) != {r["id"] for r in reqs}:
            raise ValueError("One gold answer required per requirement")
        for answer in case["gold"].values():
            checked(answer, facts)
        if not case.get("groups"):
            raise ValueError("Explicit split groups are required")
        groups = set(case["groups"])
        for row in [*facts.values(), *reqs]:
            normalized = " ".join(unicodedata.normalize("NFC", row["text"].casefold()).split())
            groups.add("exact:" + digest(normalized.encode()))
        audit_rows.append({"id": case["id"], "partition": case["partition"], "groups": sorted(groups)})
    audit = audit_splits({"schema_version": "1.0", "rows": audit_rows})
    if audit["cross_partition_component_count"]:
        raise ValueError("Connected evidence or source reused across splits")
    return data["cases"]


def examples(cases, partition):
    return [(c["id"], req, validate_packet(c["packet"]), c["gold"][req["id"]])
            for c in cases if c["partition"] == partition for req in c["packet"]["requirements"]]


def metrics(rows):
    if not rows:
        raise ValueError("Empty evaluation split")
    per_class = {}
    for label in LABELS:
        support = sum(r["gold"]["label"] == label for r in rows)
        predicted = sum((r["prediction"] or {}).get("label") == label for r in rows)
        tp = sum(r["gold"]["label"] == label and (r["prediction"] or {}).get("label") == label for r in rows)
        per_class[label] = {"support": support, "f1": (2 * tp / (support + predicted)) if support + predicted else 0.0}
    tp = found = expected = false_support = joint_exact = 0
    for row in rows:
        pred = row["prediction"] or {"label": "invalid", "fact_ids": []}
        cited, gold = set(pred["fact_ids"]), set(row["gold"]["fact_ids"])
        joint_exact += int(pred["label"] == row["gold"]["label"] and cited == gold)
        tp += len(cited & gold)
        found += len(cited)
        expected += len(gold)
        false_support += int(pred["label"] in {"direct", "partial"} and row["gold"]["label"] in {"unknown", "contradicted"})
    return {"n": len(rows), "invalid": sum(r["prediction"] is None for r in rows),
            "label_macro_f1": sum(v["f1"] for v in per_class.values()) / len(LABELS),
            "citation_micro_f1": 2 * tp / (found + expected) if found + expected else None,
            "false_support_count": false_support, "joint_exact_accuracy": joint_exact / len(rows), "per_class": per_class}


def write(path, data):
    with path.open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def command(args):
    start = time.monotonic()
    if args.command != "preview":
        cases = load_cases(args.dataset)
        selected = examples(cases, "train" if args.command == "train" else args.partition)
        if not selected:
            raise ValueError("Split contains no observations")
    model = None
    if args.backend == "qwen":
        if not args.model_dir or not args.model_revision:
            raise ValueError("Specify local checkpoint and its revision")
        from adapters.qwen35_pairing import LocalQwen
        model = LocalQwen(args.model_dir, adapter=getattr(args, "adapter", None), device=args.device)
    predict = lexical_answer
    if model:
        predict = model.choose if getattr(args, "decoding", "json") == "choice" else model.predict
    if args.command == "preview":
        packet = strict_json(args.packet.read_text(encoding="utf-8"))
        if "outcome" in packet or "data" in packet:
            packet = packet["data"]
        def predict_preview(req, facts):
            if args.top_k:
                facts = {fid: facts[fid] for fid, _ in retrieval(req, facts)[:args.top_k]}
            return checked(predict(req, facts), facts)
        result = preview(packet, predict_preview)
    else:
        result = {"schema": "evidence-run-1", "scope": "synthetic QA only", "command": args.command,
                  "dataset_sha256": digest(args.dataset.read_bytes()), "backend": args.backend,
                  "declared_model_revision": args.model_revision}
        if args.command == "train":
            result.update(model.train([(r, f, a) for _, r, f, a in selected], args.adapter_dir,
                                      args.epochs, args.seed))
        else:
            rows = []
            hits = total_gold = 0
            for case_id, req, facts, answer in selected:
                ranked = retrieval(req, facts)
                pool = ({key: facts[key] for key, _ in ranked[:args.top_k]} if args.top_k else facts)
                gold_ids = set(answer["fact_ids"])
                hits += len(gold_ids & set(pool))
                total_gold += len(gold_ids)
                err = None
                try:
                    prediction = checked(predict(req, pool), pool)
                except ValueError as exc:
                    prediction, err = None, str(exc)
                rows.append({"case": case_id, "requirement_id": req["id"], "gold": answer,
                             "prediction": prediction, "error": err, "pool": list(pool)})
            result.update({"partition": args.partition, "decoding": args.decoding if model else None, "adapter": args.adapter.name if args.adapter else None,
                           "top_k": args.top_k, "evidence_pool_recall": hits / total_gold if total_gold else None,
                           "metrics": metrics(rows), "rows": rows})
        result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    if model:
        result['checkpoint_binding'] = model.checkpoint_binding
        result['adapter_binding'] = model.adapter_binding
        result['generation_measurements'] = model.measurements
        result['device_requested'] = args.device
        result['model_quality_accepted'] = False
    write(args.output, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("evaluate", "preview", "train"):
        p = subs.add_parser(name)
        p.add_argument("--output", required=True, type=Path)
        p.add_argument("--model-dir", type=Path)
        p.add_argument('--device', choices=('cpu', 'cuda'), default='cpu',
                       help='Explicit compute choice; CUDA never falls back to CPU')
        p.add_argument("--model-revision", help="Declared upstream immutable revision for the selected local copy")
        if name == "train":
            p.set_defaults(backend="qwen")
            p.add_argument("--adapter-dir", required=True, type=Path)
            p.add_argument("--epochs", type=int, default=1)
            p.add_argument("--seed", type=int, default=17)
        else:
            p.add_argument("--backend", choices=("bm25", "qwen"), default="bm25")
            p.add_argument("--adapter", type=Path)
            p.add_argument("--decoding", choices=("json", "choice"), default="json")
            p.add_argument("--top-k", type=int, default=0)
        if name == "preview":
            p.add_argument("--packet", type=Path, required=True)
        else:
            p.add_argument("--dataset", type=Path, default=FIXTURE)
        if name == "evaluate":
            p.add_argument("--partition", choices=("train", "development", "test"), default="test")
    args = parser.parse_args()
    if getattr(args, "decoding", None) == "choice" and args.backend != "qwen":
        parser.error("Choice decoding requires Qwen")
    if getattr(args, "top_k", 0) < 0:
        parser.error("top-k must be zero or positive")
    if args.output.exists():
        parser.error("Choose a new output path")
    if getattr(args, "adapter", None) and args.backend != "qwen":
        parser.error("--adapter requires --backend qwen")
    command(args)


if __name__ == "__main__":
    main()
