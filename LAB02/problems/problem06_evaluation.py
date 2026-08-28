# -*- coding: utf-8 -*-
# Problem 06: nothing in this project measures whether retrieval works
#
# There is no evaluation code, no answer key, and no metric. The only thing
# resembling a test is four hard-coded questions in lab07 whose output is
# written to a file that nothing reads back. Every claim about how well this
# system retrieves was produced by a person reading results on screen.

import json
import os

from data_loader import BASE_DIR, head, rule, sample_questions

# สิ่งที่ระบบวัดผลต้องมี เทียบกับที่ LAB04 มีจริง
EXPECTED = [
    ("evaluation/", "โฟลเดอร์สคริปต์วัดผล"),
    ("data/golden_set.json", "เฉลยว่าคำถามไหนควรได้ chunk ไหน"),
    ("evaluation/metrics.py", "สูตร MRR / hit@k / nDCG"),
    ("outputs/eval_retrieval.json", "ผลการวัดที่บันทึกไว้"),
]


def run():
    rule("สิ่งที่ไม่มีในโปรเจกต์นี้")
    for rel, description in EXPECTED:
        exists = os.path.exists(os.path.join(BASE_DIR, rel))
        print(f"  {'มี  ' if exists else 'ไม่มี'}  {rel:<30} {description}")
    print()
    print("  ทั้งสี่อย่างมีอยู่ใน LAB04 ซึ่งเป็นระบบรุ่นถัดมาของโครงเดียวกัน")
    print()

    rule("ไฟล์ผลลัพธ์ที่มี — และสิ่งที่มันบอกไม่ได้")
    path = os.path.join(BASE_DIR, "outputs", "retrieval_results.json")
    with open(path, "r", encoding="utf-8") as f:
        results = json.load(f)

    print(f"  outputs/retrieval_results.json มี {len(results)} คำถาม")
    for row in results:
        top = row["results"][0]
        print(f"    {head(row['query'], 38):<40} -> {head(top['question'], 30)}")
    print()
    print("  มาจาก SAMPLE_QUERIES ที่เขียนตายตัวไว้ใน labs/lab07_complete_retrieval.py:24")
    print("  ไฟล์นี้บันทึกว่า 'ระบบคืนอะไรมา' ไม่ได้บันทึกว่า 'สิ่งที่คืนมานั้นถูกหรือผิด'")
    print("  ไม่มีเฉลยให้เทียบ จึงคำนวณคะแนนอะไรจากมันไม่ได้เลย")
    print()

    rule("คำถามทดสอบที่มี แต่ไม่มีใครรัน")
    questions = sample_questions()
    print(f"  data/sample_questions.txt มี {len(questions)} คำถาม")
    for query in questions[:4]:
        print(f"    {query}")
    print("    …")
    print()
    print("  grep ทั้งโปรเจกต์แล้วไม่มีสคริปต์ไหนเปิดไฟล์นี้ มีแต่ README ที่พูดถึงมัน")
    print("  ผลที่รายงานไว้ใน README จากคำถามชุดนี้ได้มาจากการรันด้วยมือแล้วอ่านผลเอง")
    print()

    rule("ทำไมถึงเป็นปัญหา")
    print("  1. ทำซ้ำไม่ได้ ผลที่รายงานไว้ตรวจสอบใหม่ไม่ได้ด้วยการรันคำสั่งเดียว")
    print("     ต้องนั่งอ่านผลทีละข้อใหม่ทั้งหมด")
    print()
    print("  2. เปรียบเทียบไม่ได้ ถ้าเปลี่ยนโมเดล เปลี่ยน CHUNK_SIZE หรือแก้คลัง")
    print("     ไม่มีตัวเลขก่อนหน้าให้เทียบว่าดีขึ้นหรือแย่ลง")
    print()
    print("  3. ตัวเลขเดียวปนสองเรื่อง การนับด้วยมือมักได้ออกมาเป็น 'ถูก 5 จาก 10'")
    print("     ซึ่งซ่อนความจริงว่าคำถามเจาะจงเมนูได้ 6/6 ส่วนคำถามที่ต้องรวมหลาย")
    print("     เมนูได้ 0/4 และกลุ่มหลังไม่มีทางถูกได้เลย (ดูปัญหาข้อ 3)")
    print()

    rule("แนวทางแก้ที่เล็กที่สุดที่ได้ผล")
    print("  คลังนี้เป็น 15 เมนู เมนูละ 6 คำถามที่โครงเหมือนกัน จึงสร้างเฉลยอัตโนมัติได้")
    print("  โดยใช้คำถามในคลังเป็นตัวตั้ง แล้วให้ chunk_id ของมันเองเป็นคำตอบที่ถูก")
    print()
    print("  แต่ต้องระวังกับดักที่ LAB04 เจอ — เฉลยแบบนั้นวัดได้แค่เพดานบน")
    print("  ถามด้วยคำถามที่ลอกมาจากคลังตรง ๆ ทุกคอนฟิกจะได้ 1.0000 เท่ากันหมด")
    print("  และแยกไม่ออกว่าอันไหนดีกว่า ต้องมีคำถามที่เขียนใหม่ด้วยมือควบคู่ไปด้วย")
    print("  ที่ LAB04 มีคำถามเขียนใหม่ 60 ข้อ และเป็นชุดเดียวที่ตัดสินอะไรได้")


if __name__ == "__main__":
    run()
