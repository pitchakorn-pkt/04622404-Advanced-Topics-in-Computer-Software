"""วัด hit@1 / hit@5 / MRR ของ BM25-only / vector-only / hybrid(RRF) เทียบกับ golden set

golden_set.json ระบุ relevant_chunk_ids เป็น "index ของคู่ถาม-ตอบเดิม" (0-based เรียงทั้งไฟล์)
ไม่ใช่ chunk_id ของเรา — ต้อง map ผ่าน source_qa_indices ที่เก็บไว้ตอน ingest ก่อนเทียบผล
(ดู docs/team/05_retrieval_knowledge.md ข้อ 3 ใต้หัวข้อ "ระวังสามข้อ")

วัดด้วย variant `paraphrase` เป็นหลัก — `verbatim` จะได้ 1.0000 ทุกคอนฟิกแล้วเทียบอะไรไม่ได้
รันด้วย: python eval_retrieval.py [--variant paraphrase] [--top-k 5]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from app import config
from app.index_store import load_bm25
from app.retrieval import search

GOLDEN_SET_PATH = os.path.join(config.DATA_DIR, "golden_set.json")


def load_golden_set() -> list[dict]:
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        return json.load(f)["items"]


def map_old_ids_to_chunk_ids() -> dict[int, set[str]]:
    """old_qa_index -> {chunk_id, ...} — คู่ถาม-ตอบเดิมหนึ่งคู่อาจตกอยู่ใน chunk มากกว่าหนึ่งอันเพราะ overlap"""
    data = load_bm25()
    if data is None:
        print("ยังไม่มีดัชนี — รัน `python ingest.py` ก่อน", file=sys.stderr)
        sys.exit(1)
    _, records = data
    mapping: dict[int, set[str]] = {}
    for r in records:
        for old_idx in r.source_qa_indices:
            mapping.setdefault(old_idx, set()).add(r.chunk_id)
    return mapping


def evaluate(method: str, golden: list[dict], id_map: dict[int, set[str]], variant: str, top_k: int) -> dict:
    hits_at_1 = 0
    hits_at_5 = 0
    reciprocal_ranks = []
    unmapped = []

    for item in golden:
        old_id = item["relevant_chunk_ids"][0]
        relevant_chunk_ids = id_map.get(old_id)
        if not relevant_chunk_ids:
            unmapped.append(item["id"])
            reciprocal_ranks.append(0.0)
            continue

        query = item["variants"].get(variant) or item["variants"]["verbatim"]
        results = search(query, top_k=max(top_k, 5), method=method)
        ranked_ids = [hit.record.chunk_id for hit in results]

        rank = next((i + 1 for i, cid in enumerate(ranked_ids) if cid in relevant_chunk_ids), None)
        if rank == 1:
            hits_at_1 += 1
        if rank is not None and rank <= 5:
            hits_at_5 += 1
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)

    n = len(golden)
    return {
        "method": method,
        "hit@1": hits_at_1 / n,
        "hit@5": hits_at_5 / n,
        "mrr": sum(reciprocal_ranks) / n,
        "unmapped": unmapped,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="paraphrase",
                         help="ตัว variant ที่ใช้ยิงคำถาม (default: paraphrase — อย่าใช้ verbatim, ดู docstring)")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    golden = load_golden_set()
    id_map = map_old_ids_to_chunk_ids()

    still_unmapped_ids = {item["relevant_chunk_ids"][0] for item in golden} - set(id_map.keys())
    if still_unmapped_ids:
        print(f"[warn] {len(still_unmapped_ids)} old_qa_index ใน golden set หา chunk ใหม่ไม่เจอ: "
              f"{sorted(still_unmapped_ids)}", file=sys.stderr)

    rows = [evaluate(m, golden, id_map, args.variant, args.top_k) for m in ("bm25", "vector", "hybrid", "rerank")]

    print(f"\nวัดด้วย variant `{args.variant}` บน golden set {len(golden)} ข้อ (top_k={args.top_k})\n")
    header = "| วิธีค้น | hit@1 | hit@5 | MRR |"
    sep = "|---|---|---|---|"
    label = {
        "bm25": "BM25 อย่างเดียว", "vector": "vector อย่างเดียว", "hybrid": "hybrid (RRF)",
        "rerank": "hybrid + cross-encoder rerank",
    }
    lines = [header, sep]
    for row in rows:
        lines.append(f"| {label[row['method']]} | {row['hit@1']:.4f} | {row['hit@5']:.4f} | {row['mrr']:.4f} |")
    table = "\n".join(lines)
    print(table)

    if rows[0]["unmapped"]:
        print(f"\n[warn] golden item ที่ map chunk ไม่เจอเลย: {rows[0]['unmapped']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
