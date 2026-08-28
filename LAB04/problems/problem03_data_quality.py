# -*- coding: utf-8 -*-
# Problem 03: what the corpus is made of decides what the system can be right about
#
# Three checks, all run against the committed corpus:
#   1. integrity  — did the parser lose anything on the way in?
#   2. duplicates — how close do the nearest two entries sit?
#   3. the parser — what does load_qa_file() swallow without saying a word?
#
# The failure that actually cost this project a rebuild is none of the three.
# It was factual: the previous corpus stated things that were not true, and no
# retrieval metric can see that, because every metric here compares chunk ids.

import os
import tempfile

from data_loader import head, load_chunks, load_embeddings, load_records, rule, source_lines

from src.document_loader import load_qa_file

# ตัวอย่างคลังที่รูปแบบเพี้ยน — ใช้ทดสอบว่า parser เงียบแค่ไหน
MALFORMED = """[หมวด: หมวดที่หนึ่ง]
Q: คำถามที่มีคำตอบครบ
A: คำตอบที่หนึ่ง

Q: คำถามที่ไม่มีบรรทัด A ตามมา

Q: คำถามถัดไปหลังจากข้อที่หายไป
A: คำตอบที่สอง

หมวด: หมวดที่สอง (ลืมวงเล็บเหลี่ยม)
Q: คำถามที่ควรอยู่หมวดที่สอง
A: คำตอบที่สาม
"""


def check_integrity():
    rule("1. ตรวจว่าขั้นอ่านไฟล์ทำข้อมูลหายไหม")
    lines = source_lines()
    n_q = sum(1 for l in lines if l.strip().startswith("Q:"))
    n_a = sum(1 for l in lines if l.strip().startswith("A:"))
    records = load_records()
    no_category = sum(1 for r in records if r["category"] == "ไม่ระบุหมวด")
    questions = [r["question"] for r in records]

    print(f"  บรรทัด Q: ในไฟล์      {n_q}")
    print(f"  บรรทัด A: ในไฟล์      {n_a}")
    print(f"  record ที่ parse ได้   {len(records)}")
    print(f"  record ที่ไม่มีหมวด    {no_category}")
    print(f"  คำถามซ้ำกันเป๊ะ ๆ      {len(questions) - len(set(questions))}")
    print()
    if n_q == n_a == len(records) and no_category == 0:
        print("  คลังชุดนี้ผ่านทั้งสี่ข้อ — ไม่ได้แปลว่าโค้ดปลอดภัย แปลว่าไฟล์บังเอิญถูกต้อง")
        print("  ดูข้อ 3 ว่าถ้าไฟล์ไม่ถูกต้องจะเกิดอะไรขึ้น")
    print()


def check_duplicates():
    rule("2. สองรายการที่ใกล้กันที่สุดในคลัง")
    import numpy as np

    chunks = load_chunks()
    vectors = load_embeddings()
    similarity = vectors @ vectors.T        # normalize มาแล้ว dot = cosine
    np.fill_diagonal(similarity, -1)

    pairs = []
    for i in range(len(chunks)):
        j = int(similarity[i].argmax())
        if i < j:
            pairs.append((float(similarity[i][j]), i, j))
    pairs.sort(reverse=True)

    over_90 = sum(1 for score, _, _ in pairs if score > 0.90)
    over_85 = sum(1 for score, _, _ in pairs if score > 0.85)
    print(f"  คู่ที่ cosine > 0.90 : {over_90}")
    print(f"  คู่ที่ cosine > 0.85 : {over_85}")
    print()
    for score, i, j in pairs[:5]:
        same = "หมวดเดียวกัน" if chunks[i]["category"] == chunks[j]["category"] else "คนละหมวด  "
        print(f"  {score:.4f}  {same}")
        print(f"      [{i:3}] {head(chunks[i]['question'], 56)}")
        print(f"      [{j:3}] {head(chunks[j]['question'], 56)}")
    print()
    print("  ไม่มีคู่ไหนแตะ 0.90 จึงไม่มีรายการซ้ำที่ต้องลบ ที่เห็นคือของที่ตั้งใจใส่")
    print("  ตอนขยายคลังจาก 172 เป็น 194 คู่ เติมไป 22 ข้อให้เป็นตัวลวงที่นั่งใกล้ของเดิม")
    print()
    print("  ผลของการเติม: ค่าเฉลี่ยแทบไม่ขยับ (ผิดจาก 3 เป็น 4 ข้อ) แต่จำนวนข้อที่")
    print("  พลิกระหว่างคอนฟิกกว้างขึ้น และ p ดีขึ้นสิบเท่า — คลังที่ทุกข้อห่างกันมาก")
    print("  จะให้คะแนนสูงสวยแต่แยกไม่ออกว่าคอนฟิกไหนดีกว่า (ดูปัญหาข้อ 9)")
    print()


def check_parser():
    rule("3. parser เงียบแค่ไหนเมื่อไฟล์ผิดรูปแบบ")
    path = os.path.join(tempfile.gettempdir(), "malformed_qa.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(MALFORMED)

    print("  ไฟล์ทดสอบมี 4 บรรทัด Q: และ 3 บรรทัด A: กับหัวข้อหมวดที่ลืมวงเล็บ 1 บรรทัด")
    print()
    records = load_qa_file(path)
    print(f"  load_qa_file() คืน record มา {len(records)} รายการ โดยไม่เตือนอะไรเลย:")
    for r in records:
        print(f"      หมวด {r['category']:<32} | {head(r['question'], 34)}")
    os.remove(path)
    print()
    print("  สองอย่างที่หายไปเงียบ ๆ:")
    print('    - "คำถามที่ไม่มีบรรทัด A ตามมา" ถูกทิ้ง เพราะเงื่อนไขที่')
    print("      document_loader.py:36 บังคับว่าต้องมี A: ตามหลัง Q: ถึงจะเก็บ")
    print('    - "หมวดที่สอง" ที่ลืมวงเล็บเหลี่ยมไม่ถูกอ่านเป็นหัวข้อหมวด')
    print("      (document_loader.py:31 ดูแค่ว่าขึ้นต้นด้วย [หมวด ไหม)")
    print("      record ข้อสุดท้ายจึงตกไปอยู่หมวดที่หนึ่งทั้งที่ควรอยู่หมวดที่สอง")
    print()
    print("  วิธีตรวจ: นับบรรทัด Q: กับ A: ในไฟล์ แล้วเทียบกับ len(records) ทุกครั้ง")
    print("  ที่แก้คลัง ตามที่ข้อ 1 ทำ ตัว build_index.py เองไม่ได้ตรวจให้")
    print()


def factual_errors():
    rule("4. ปัญหาที่แพงที่สุด และตัววัดทุกตัวมองไม่เห็น — ข้อเท็จจริงผิด")
    print("  คลังชุดแรกของ LAB04 เป็นโดเมน IoT/Embedded ตรวจข้อเท็จจริงแล้ว")
    print("  พบผิด 5 จาก ~15 ข้อที่ไล่ตรวจ ตัวอย่าง:")
    print("    - ESP32 บูตที่ 115200 ไม่ใช่ 74880 (74880 เป็นของ ESP8266)")
    print("    - กระแสต่อขา 12 mA ไม่ใช่ตัวเลขที่ Espressif ระบุ")
    print("    - ขนาดบอร์ด XIAO และรุ่นกล้องที่ระบุไว้ไม่ตรงกับสเปกจริง")
    print()
    print("  ทำไมตัววัดจับไม่ได้: eval_retrieval เทียบ chunk_id ที่ค้นเจอกับ chunk_id")
    print("  ที่เฉลยระบุไว้ ถ้าค้นเจอ chunk ที่ถูกชิ้น ก็ได้คะแนนเต็ม ไม่ว่าเนื้อใน")
    print("  chunk นั้นจะจริงหรือไม่ ระบบจึง 'ค้นถูกแล้วตอบผิด' ได้อย่างสมบูรณ์")
    print()
    print("  แก้โดยเปลี่ยนโดเมนทั้งคลังเป็นปัญหามือถือ/คอมพิวเตอร์ในชีวิตประจำวัน")
    print("  ซึ่งคำตอบเป็นคำแนะนำเชิงวิธีการ ไม่ใช่ตัวเลขสเปกที่ต้องไล่ตรวจกับเอกสาร")
    print()
    print("  บทเรียน: อย่าสร้าง dataset ที่มีตัวเลขสเปก ถ้าไม่มีเวลาไล่ตรวจทีละข้อ")
    print("  กับเอกสารต้นทางจริง")


def run():
    check_integrity()
    check_duplicates()
    check_parser()
    factual_errors()


if __name__ == "__main__":
    run()
