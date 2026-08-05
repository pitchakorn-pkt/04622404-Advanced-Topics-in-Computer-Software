# eval_query_transform.py
# วัดว่าขั้น "ปรับคำถามก่อนค้น" คุ้มหรือไม่
#
# eval_retrieval.py วัดตั้งแต่ขั้นค้นหาเป็นต้นไป ส่วนไฟล์นี้วัดขั้นที่อยู่ก่อนหน้านั้น
# โดยเทียบ 6 แบบบนระบบเดียวกัน (hybrid + rerank ตามค่าที่ shipped)
#
#     ดิบ                        ส่งคำถามเข้าไปตรง ๆ
#     normalize ไม่มี SLANG_MAP  ตัดคำลงท้ายกับยุบช่องว่างอย่างเดียว
#     normalize + SLANG_MAP      แบบที่ระบบใช้จริง ไม่เรียก LLM
#     rewrite / multi_query / hyde   เรียก LLM หนึ่งครั้งต่อคำถาม
#
# วัด 2 รูปแบบคำถาม: paraphrase (เขียนใหม่ด้วยมือ) และ slang (สลับเป็นคำทับศัพท์ไทย)
#
# ต้องมีคีย์ก่อนถ้าจะวัดสามแบบท้าย:  export GROQ_API_KEY=...
# Run: python -m evaluation.eval_query_transform

import json
import time

import config
from evaluation.metrics import average, evaluate_one, print_table

VARIANTS = ["paraphrase", "slang"]
LLM_MODES = ["rewrite", "multi_query", "hyde"]


class CountingLLM:
    """
    ห่อ LLM ไว้เพื่อนับว่าการเรียกล้มเหลวกี่ครั้ง

    จำเป็นเพราะ QueryTransformer.transform() ดักข้อผิดพลาดแล้วคืนคำถามเดิมเงียบ ๆ
    ซึ่งดีตอนใช้งานจริง แต่ตอนวัดผลจะได้ตัวเลขที่ดูสมเหตุสมผลทั้งที่ขั้นที่กำลังวัด
    ไม่ได้ทำงานเลย โดยเฉพาะโหมด rewrite ที่คืนค่าหน้าตาเหมือนกันทั้งสำเร็จและล้มเหลว
    """

    def __init__(self, llm):
        self.llm = llm
        self.model = getattr(llm, "model", "")
        self.calls = 0
        self.failures = 0

    def chat(self, messages):
        self.calls += 1
        try:
            return self.llm.chat(messages)
        except Exception:
            self.failures += 1
            raise


def build_queries(mode, query, transformer, qt, original_slang):
    """คืนรายการคำค้นตามโหมด — ตัวแรกคือคำค้นหลัก ที่เหลือเป็นคำค้นเสริม"""
    if mode == "raw":
        return [query]

    if mode == "normalize_no_slang":
        # ปิดตารางแทนคำชั่วคราวเพื่อแยกให้เห็นว่าส่วนไหนของ normalize_query มีผล
        qt.SLANG_MAP.clear()
        try:
            return [qt.normalize_query(query)]
        finally:
            qt.SLANG_MAP.update(original_slang)

    if mode == "normalize":
        return [qt.normalize_query(query)]

    config.USE_QUERY_TRANSFORM = True
    config.QUERY_TRANSFORM_MODE = mode
    try:
        return transformer.transform(query)
    finally:
        config.USE_QUERY_TRANSFORM = False


def main():
    print("=== วัดขั้นปรับคำถามก่อนค้น ===")

    config.USE_HYBRID = True

    from src import query_transform as qt
    from src.generator import get_llm
    from src.hybrid_retriever import HybridRetriever
    from src.rerankers import get_reranker

    golden = json.load(open(config.GOLDEN_SET_FILE, encoding="utf-8"))["items"]
    retriever = HybridRetriever(reranker=get_reranker())
    llm = CountingLLM(get_llm())
    transformer = qt.QueryTransformer(llm)
    original_slang = dict(qt.SLANG_MAP)

    modes = ["raw", "normalize_no_slang", "normalize"]
    if getattr(llm, "model", "") != "don't use LLM":
        modes += LLM_MODES
    else:
        print("! ไม่มี LLM ใช้งานได้ — ข้ามโหมด rewrite / multi_query / hyde\n")

    print(f"จำนวนข้อ: {len(golden)} | รูปแบบคำถาม: {', '.join(VARIANTS)}\n")

    results = {}
    for mode in modes:
        start_time = time.time()
        rows = {variant: [] for variant in VARIANTS}
        calls_before, failures_before = llm.calls, llm.failures

        for item in golden:
            for variant in VARIANTS:
                query = item["variants"].get(variant)
                if not query:
                    continue

                queries = build_queries(mode, query, transformer, qt, original_slang)

                chunks = retriever.retrieve(queries[0], top_k=10, extra_queries=queries[1:])
                found = [chunk["chunk_id"] for chunk in chunks]
                rows[variant].append(
                    evaluate_one(found, item["relevant_chunk_ids"], config.EVAL_K_VALUES))

        n_queries = sum(len(r) for r in rows.values())
        calls = llm.calls - calls_before
        failures = llm.failures - failures_before
        results[mode] = {
            "by_variant": {v: average(r) for v, r in rows.items() if r},
            "sec_per_query": round((time.time() - start_time) / n_queries, 2),
            "llm_calls": calls,
            "llm_failures": failures,
            "usable": failures == 0,
        }
        note = f"  [เรียก LLM {calls} ครั้ง ล้มเหลว {failures}]" if calls else ""
        warn = "  << ตัวเลขแถวนี้ใช้ไม่ได้" if failures else ""
        print(f"  {mode:20s} เสร็จใน {time.time() - start_time:.1f}s{note}{warn}")

    columns = ["hit@1", "hit@10", "mrr", "ndcg@3"]
    for variant in VARIANTS:
        print(f"\n=== รูปแบบ: {variant} ===")
        print_table({m: r["by_variant"].get(variant, {}) for m, r in results.items()}, columns)

    print("\n=== ความเร็ว ===")
    for mode, report in results.items():
        print(f"  {mode:20s} {report['sec_per_query']:7.2f} วินาทีต่อคำถาม")

    out_file = config.EVAL_QUERY_TRANSFORM_FILE
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"n_items": len(golden), "results": results}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nบันทึกรายงานที่ {out_file}")


if __name__ == "__main__":
    main()
