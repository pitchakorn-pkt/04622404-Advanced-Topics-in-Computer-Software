# -*- coding: utf-8 -*-
# Problem 07: retrieval hands over the right passage and the answer still drifts
#
# On the 20 generation questions the retriever found the right chunk 95% of the
# time and every answer carried a citation — yet correctness came out at 0.5957.
# The gap between those numbers is this problem.
#
# It comes with a second, quieter problem: the three quality numbers reported
# here are word overlap, not judgement. An answer that contradicts its own
# source can still score well, so these metrics cannot detect the thing they
# are named after.

from data_loader import head, load_eval_generation, rule

# ตัวอย่างที่เจอจริงตอนรัน gpt-oss-120b — ถามซ้ำอีกครั้งไม่เกิด ไม่ใช่ปัญหาเป็นระบบ
CONTRADICTION = {
    "chunk": "เครื่องจะหยุดจ่ายไฟเมื่อแบตเต็ม",
    "answer": "แม้แบตเต็มแล้วเครื่องยังจ่ายไฟเข้าแบต",
}


def run():
    data = load_eval_generation()
    summary = data["summary"]
    rows = data["results"]

    rule("อาการ — ค้นถูกแล้ว แต่คำตอบยังเชื่อถือไม่ได้เต็มที่")
    print(f"  จำนวนข้อที่วัด          {summary['จำนวนข้อ']}")
    print(f"  อัตราค้นเจอ chunk ที่ถูก {summary['อัตราค้นเจอ chunk ที่ถูก']:.4f}")
    print(f"  มีการอ้างอิง [n]        {summary['มีการอ้างอิง [n]']:.4f}")
    print(f"  faithfulness           {summary['faithfulness']:.4f}")
    print(f"  correctness            {summary['correctness']:.4f}   <-- ต่ำสุดในสามตัว")
    print(f"  relevance              {summary['relevance']:.4f}")
    print()
    print("  ค้นเจอ 95% และอ้างอิงครบ 100% แต่ correctness ได้ 0.60")
    print("  ขั้นค้นหาทำงานของมันเสร็จแล้ว ส่วนที่เหลือเสียตรงขั้นเขียนคำตอบ")
    print()

    rule("ข้อที่ค้นเจอ chunk ที่ถูก แต่ faithfulness ต่ำที่สุด 3 ข้อ")
    hit_rows = [r for r in rows if r["context_hit"]]
    for row in sorted(hit_rows, key=lambda r: r["faithfulness"])[:3]:
        print(f"  {row['id']}  faithfulness {row['faithfulness']:.4f}  correctness {row['correctness']:.4f}")
        print(f"      ถาม : {head(row['query'], 60)}")
        print(f"      ตอบ : {head(row['answer'], 60)}")
        print()

    rule("ตัวอย่างที่ขัดกับแหล่งอ้างอิงตรง ๆ (เจอจริง 1 ครั้ง)")
    print(f"  chunk [1] ที่ส่งให้ : {CONTRADICTION['chunk']}")
    print(f"  คำตอบที่เขียนออกมา : {CONTRADICTION['answer']}")
    print()
    print("  คำตอบอ้างอิง [1] อย่างถูกต้องตามรูปแบบ แต่เนื้อความขัดกับ [1] เอง")
    print("  ถามซ้ำอีกครั้งไม่เกิดอาการเดิม จึงไม่ใช่ปัญหาเป็นระบบ แต่เป็นหลักฐานว่า")
    print("  การมีเลขอ้างอิงไม่ได้รับประกันว่าเนื้อหาตรงกับที่อ้าง")
    print()

    rule("ทำไมตัววัดถึงจับเคสข้างบนไม่ได้")
    print("  faithfulness = word_overlap(คำตอบ, context)      (eval_generation.py:78)")
    print("  correctness  = word_overlap(คำตอบ, คำตอบเฉลย)     (eval_generation.py:79)")
    print("  relevance    = word_overlap(คำถาม, คำตอบ)         (eval_generation.py:80)")
    print()
    print("  ทั้งสามตัวคือสัดส่วนคำที่ซ้ำกัน ไม่ใช่การตัดสินว่าเนื้อความตรงกันไหม")
    print('  คำตอบที่เขียนว่า "ยังจ่ายไฟ" กับ chunk ที่เขียนว่า "หยุดจ่ายไฟ" ใช้คำ')
    print("  แทบทั้งหมดร่วมกัน จึงได้ faithfulness สูง ทั้งที่ความหมายตรงข้ามกัน")
    print()
    print("  แปลว่าเลข faithfulness 0.7862 ข้างบนอ่านได้แค่ว่า 'คำตอบใช้คำจาก context")
    print("  เป็นส่วนใหญ่' ไม่ได้แปลว่า 'คำตอบซื่อตรงต่อ context'")
    print()

    rule("เครื่องมือที่เตรียมไว้แล้วแต่ยังไม่ได้ต่อสาย")
    print("  JUDGE_PROMPT อยู่ที่ prompt_templates.py:97 เขียนเสร็จแล้ว ให้ LLM ให้คะแนน")
    print("  1-5 พร้อมเหตุผล เป็น JSON")
    print()
    print("  grep ทั้งโปรเจกต์แล้วไม่มีไฟล์ไหน import หรือเรียกใช้เลยสักที่")
    print("  ขั้นวัดผลจึงยังเป็นการนับคำซ้ำล้วน")
    print()
    print("  เหตุผลที่ยังไม่ทำ: ถ้าเปิดใช้จะได้ตัวเลขชุดใหม่ที่อาจขัดกับตัวเลขใน README")
    print("  และสไลด์ที่รายงานไปแล้ว จึงเลื่อนไว้ทำตอนต่อยอด ไม่ใช่ทำก่อนส่ง")
    print()

    rule("สิ่งที่แก้ไปแล้วในขั้นนี้")
    print("  1. ธง no_context เดิมเป็น False เสมอเมื่อมี chunk ทำให้ผู้เรียกเข้าใจผิดว่า")
    print("     ระบบตอบได้ทุกครั้ง แก้เป็นดูจากข้อความปฏิเสธของ LLM แทน (generator.py:99-102)")
    print()
    print("  2. กฎใน SYSTEM_PROMPT ข้อ 2 กับ 3 เคยขัดกันเอง — ข้อ 2 สั่งให้ตอบข้อความ")
    print('     ปฏิเสธคำเดียวจบ ส่วนข้อ 3 สั่งให้ใส่เลขอ้างอิงท้ายประโยคที่ใช้ข้อมูล')
    print('     ผลคือได้คำตอบหน้าตา "ไม่พบข้อมูล [1][2][3]" แก้โดยเติมเงื่อนไข')
    print("     ห้ามใส่หมายเลขอ้างอิงเข้าไปในกฎข้อ 2 (prompt_templates.py:16)")
    print()
    print("  3. NoLLM เดิมแยก prompt ด้วยคีย์ภาษาอังกฤษ ทั้งที่ prompt เป็นภาษาไทย")
    print("     แก้เป็นใช้ค่าคงที่ตัวเดียวกันทั้งสองฝั่ง (prompt_templates.py:24-25)")


if __name__ == "__main__":
    run()
