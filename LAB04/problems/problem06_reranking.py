# -*- coding: utf-8 -*-
# Problem 06: first-stage retrieval puts the right document too far down
#
# Numbers come from outputs/eval_retrieval.json, which was produced by running
# the same 60 questions through all four retrieval settings. The paraphrase
# variant is the one that decides anything — the other four sit at 1.0000 for
# every setting and cannot separate them (see problem 09).

from data_loader import head, load_chunks, load_eval_retrieval, rule

# เคสจริงจากการรันวันนำเสนอ 19 ส.ค. 2026 — ทำซ้ำได้เหมือนเดิมทุกครั้ง
DEMO_QUESTION = "มือถือตกน้ำต้องทำอะไรก่อน"
DEMO_RRF = [(16, 0.02407, 1), (90, 0.02264, 5)]     # (chunk_id, คะแนน RRF, อันดับ)
DEMO_RERANK_TOP = (90, 0.718)

# คะแนนที่ cross-encoder ให้กับข้อความที่ไม่ใช่คำถามเลย
NOT_QUESTIONS = [("ช่วยหน่อย", 0.8161), ("hello", 0.7271)]


def run():
    data = load_eval_retrieval()
    results = data["results"]
    chunks = load_chunks()

    rule(f"ผลการวัดจริง — คำถาม {data['n_items']} ข้อ variant paraphrase")
    print(f"  {'คอนฟิก':<18}{'MRR':>9}{'hit@1':>9}{'hit@10':>9}{'ms/คำถาม':>11}")
    for name in ["dense_only", "bm25_only", "hybrid", "hybrid+rerank"]:
        r = results[name]
        p = r["by_variant"]["paraphrase"]
        print(f"  {name:<18}{p['mrr']:>9.4f}{p['hit@1']:>9.4f}{p['hit@10']:>9.4f}{r['ms_per_query']:>11.1f}")
    print()

    hybrid = results["hybrid"]["by_variant"]["paraphrase"]
    full = results["hybrid+rerank"]["by_variant"]["paraphrase"]
    print(f"  hit@10 ขยับจาก {hybrid['hit@10']:.4f} เป็น {full['hit@10']:.4f} — แทบไม่ต่าง")
    print(f"  hit@1  ขยับจาก {hybrid['hit@1']:.4f} เป็น {full['hit@1']:.4f} — ต่างกันมาก")
    print()
    print("  คู่ตัวเลขนี้คือตัวปัญหาทั้งหมดในบรรทัดเดียว: เอกสารที่ถูกอยู่ใน 10 อันดับแรก")
    print("  อยู่แล้วเกือบทุกข้อ ขั้นค้นหาจึงไม่ได้ 'หาไม่เจอ' มันแค่ 'เรียงไม่เป็น'")
    print("  และผู้ใช้เห็นแค่ 3 อันดับแรก (TOP_K = 3) ของที่อยู่อันดับ 5 จึงเท่ากับไม่มี")
    print()

    rule("สาเหตุ")
    print("  ขั้นแรกใช้ bi-encoder — เข้ารหัสคำถามกับเอกสารแยกกันคนละครั้ง แล้ววัดระยะ")
    print("  เอกสารถูกเข้ารหัสไว้ล่วงหน้าตั้งแต่ตอน build index โดยยังไม่รู้ว่าใครจะถามอะไร")
    print("  มันจึงเก่งเรื่อง 'เรื่องนี้ใกล้เคียงกัน' แต่ไม่เก่งเรื่อง 'อันไหนตอบคำถามนี้'")
    print()
    print("  RRF ที่รวมอันดับ (hybrid_retriever.py:59-77) ก็ไม่ได้ช่วยเรื่องนี้ เพราะมันดู")
    print("  แค่ 'อันดับที่เท่าไหร่' ของแต่ละวิธี ไม่ได้ดูเนื้อหาเลย")
    print()

    rule("เคสจริงที่ทำซ้ำได้ — RRF จัดผิด แล้ว cross-encoder ดึงกลับ")
    print(f'  คำถาม: "{DEMO_QUESTION}"')
    print()
    print("  หลัง RRF (ก่อน rerank):")
    for chunk_id, score, rank in DEMO_RRF:
        mark = "  <-- ที่ถูก แต่ผู้ใช้ไม่เห็นเพราะ TOP_K = 3" if chunk_id == DEMO_RERANK_TOP[0] else ""
        print(f"    อันดับ {rank}  {score:.5f}  [{chunk_id:3}] {head(chunks[chunk_id]['question'], 34)}{mark}")
    print()
    cid, score = DEMO_RERANK_TOP
    print(f"  หลัง rerank:")
    print(f"    อันดับ 1  {score:.3f}    [{cid:3}] {head(chunks[cid]['question'], 34)}")
    print()
    print(f"  chunk 16 อยู่หมวด '{chunks[16]['category']}' ส่วน chunk 90 อยู่หมวด")
    print(f"  '{chunks[90]['category']}' — เป็นเคสเดียวกับที่ปัญหาข้อ 5 พูดถึง")
    print("  ถ้ามีการกรองด้วยหมวด เคสนี้จะไม่เกิดตั้งแต่แรก")
    print()

    rule("ราคาที่ต้องจ่าย")
    hy_ms = results["hybrid"]["ms_per_query"]
    full_ms = results["hybrid+rerank"]["ms_per_query"]
    print(f"  เวลาต่อคำถาม {hy_ms:.1f} ms -> {full_ms:.1f} ms  (ช้าลง {full_ms/hy_ms:.0f} เท่า)")
    print("  โมเดลเพิ่มอีกราว 2.2 GB ต้องโหลดตอนเริ่มระบบ")
    print()
    print("  ยังคุ้มอยู่ เพราะเวลาที่ LLM ใช้เขียนคำตอบอยู่ที่ราว 1.4 วินาที")
    print("  ครึ่งวินาทีของขั้น rerank จึงเป็นส่วนน้อยของเวลาที่ผู้ใช้รอจริง")
    print()

    rule("กับดักที่เจอ — คะแนน rerank เอาไปตั้งเกณฑ์ตัดไม่ได้")
    for text, score in NOT_QUESTIONS:
        print(f'    "{text}" ได้คะแนน {score:.4f}')
    print("    ส่วนคำถามจริงบางข้อได้แค่ 0.0012")
    print()
    print("  cross-encoder ถูกฝึกให้ 'เรียงลำดับ' ไม่ได้ถูกฝึกให้บอก 'ความน่าจะเป็น'")
    print("  คะแนนของมันเทียบข้ามคำถามไม่ได้ ใช้ได้แค่ภายในคำถามเดียวกัน")
    print("  เกณฑ์ rerank ที่ดีที่สุดที่ลองแล้วยังปฏิเสธคำถามจริงผิด 4 จาก 60 ข้อ")
    print("  เกณฑ์ตัดจึงต้องใช้คะแนน dense แทน (ดูปัญหาข้อ 1)")
    print()

    rule("วิธีตรวจสอบว่าขั้นนี้คุ้มไหมกับคลังอื่น")
    print("  ดูส่วนต่างระหว่าง hit@1 กับ hit@10 ของคอนฟิกที่ยังไม่ rerank")
    print("  ห่างมาก = ค้นเจอแต่เรียงไม่เป็น rerank จะช่วยได้เยอะ")
    print("  ห่างน้อย = ค้นไม่เจอตั้งแต่แรก ต้องไปแก้ที่ขั้น embedding หรือคลัง ไม่ใช่ rerank")


if __name__ == "__main__":
    run()
