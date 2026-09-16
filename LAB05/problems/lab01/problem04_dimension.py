# -*- coding: utf-8 -*-
# Problem 04: a query embedded differently from the corpus finds nothing useful
#
# Retrieval compares a query vector against stored vectors. That comparison is
# only meaningful if both were produced by the same provider, model and width.
# Nothing about a vector says which one made it, so the pipeline has to carry
# that information itself — and where it does not, the failure is silent.

import os
import re

from data_loader import PIPELINE, rule

# vector_store.py import chromadb ตอนโหลดโมดูล ซึ่งไม่ได้ติดตั้งไว้ใน venv นี้
# จึงดึงเฉพาะตัวฟังก์ชันที่ต้องการออกมาจากไฟล์จริงแล้วรัน แทนการ import ทั้งโมดูล
# โค้ดที่รันจึงเป็นโค้ดตัวเดียวกับที่ระบบใช้ ไม่ใช่สำเนาที่เขียนขึ้นใหม่
_SOURCE = open(os.path.join(PIPELINE, "vector_store.py"), encoding="utf-8").read()


def _extract(name):
    """ดึงโค้ดของฟังก์ชันชื่อ name ออกมาจาก vector_store.py ตามที่มันเป็น"""
    match = re.search(rf"^def {name}\(.*?(?=^\S|\Z)", _SOURCE, re.S | re.M)
    if not match:
        raise SystemExit(f"หา def {name} ใน vector_store.py ไม่เจอ")
    return match.group()


def _constant(name):
    match = re.search(rf"^{name}\s*=\s*(.+)$", _SOURCE, re.M)
    return match.group(1).split("#")[0].strip() if match else "(หาไม่เจอ)"


_namespace = {}
exec(_extract("embedding_settings"), _namespace)
embedding_settings = _namespace["embedding_settings"]
DEFAULT_PROVIDER = _constant("DEFAULT_PROVIDER")
DEFAULT_MODEL = _constant("DEFAULT_MODEL")

# record ตัวอย่างที่บันทึกว่าถูก embed มาด้วยค่าอะไร
SAME = [
    {"model": "BAAI/bge-small-en-v1.5", "dimension": 384},
    {"model": "BAAI/bge-small-en-v1.5", "dimension": 384},
]
MIXED_MODEL = [
    {"model": "BAAI/bge-small-en-v1.5", "dimension": 384},
    {"model": "gemini-embedding-001", "dimension": 384},
]
MIXED_WIDTH = [
    {"model": "BAAI/bge-small-en-v1.5", "dimension": 384},
    {"model": "BAAI/bge-small-en-v1.5", "dimension": 1536},
]


def try_settings(label, records):
    try:
        model, dimension = embedding_settings(records)
        print(f"  {label:<28} ผ่าน — {model} · {dimension} มิติ")
    except AssertionError as error:
        print(f"  {label:<28} หยุด  — {error}")


def run():
    rule("สามอย่างที่ต้องตรงกันระหว่างตอนสร้างดัชนีกับตอนค้น")
    print("  provider   ผู้ให้บริการที่เข้ารหัส (local / gemini / openai)")
    print("  model      ชื่อโมเดล")
    print("  dimension  ความกว้างของเวกเตอร์")
    print()
    print("  เวกเตอร์ไม่ได้บอกว่าใครสร้างมัน ตัวเลข 384 ตัวจาก bge กับจาก gemini")
    print("  หน้าตาเหมือนกันทุกประการ ระบบจึงต้องพกข้อมูลนี้ไปเอง")
    print()

    rule("ด่านที่มีอยู่ — embedding_settings() (vector_store.py:140-150)")
    try_settings("record ที่ตรงกันทั้งหมด", SAME)
    try_settings("คนละโมเดล", MIXED_MODEL)
    try_settings("คนละความกว้าง", MIXED_WIDTH)
    print()
    print("  ทั้งสองกรณีที่ปนกันถูกหยุดก่อนถึงขั้นค้น เพราะ record แต่ละอันบันทึก")
    print("  model กับ dimension ที่ใช้เข้ารหัสตัวเองไว้ และฟังก์ชันนี้ยืนยันว่ามีค่าเดียว")
    print()

    rule("ด่านที่สอง — ความกว้างของ collection")
    print("  create_collection() เขียน dimension ลง metadata ของ collection")
    print("  (vector_store.py:232-233) แล้ว upsert() เทียบความกว้างของเวกเตอร์ที่")
    print("  กำลังจะใส่กับค่านั้นทุกครั้ง (vector_store.py:248-255)")
    print()
    print("  จำเป็นเพราะ Chroma ไม่บังคับ schema ของความกว้างเอง เวกเตอร์ 1536 มิติ")
    print("  ที่ใส่เข้า collection ที่สร้างไว้สำหรับ 384 จะไม่ถูกปฏิเสธโดยตัวมันเอง")
    print()
    print("  นี่คือเหตุผลที่การเปลี่ยน provider ต้องใช้ collection คนละอัน:")
    print("    python Pipeline/05_embedding.py --provider gemini --dimension 1536")
    print("    python main.py --build --collection job_postings_gemini \\")
    print("                          --persist-dir Pipeline/chroma_gemini")
    print()

    rule("ช่องที่ยังเหลือ — provider")
    print(f"  ค่าเริ่มต้นที่ระบบใช้ตอนค้น  provider={DEFAULT_PROVIDER}  model={DEFAULT_MODEL}")
    print("  (vector_store.py:64 — 'What a collection is assumed to have been")
    print("   embedded with when it does not say')")
    print()
    print("  collection ที่ไม่ได้บันทึก provider ไว้จะถูก 'สันนิษฐาน' ว่าเป็นค่าเริ่มต้น")
    print("  ถ้าคลังนั้นถูกสร้างด้วย provider อื่นแต่ความกว้างบังเอิญตรงกัน")
    print("  ด่านทั้งสองข้างบนจะผ่านหมด แล้วการค้นจะทำงานต่อโดยไม่มีข้อผิดพลาด")
    print()
    print("  ผลที่ได้ไม่ใช่ error แต่เป็นคะแนนความคล้ายที่ไร้ความหมาย เพราะสองปริภูมิ")
    print("  เวกเตอร์ที่ไม่เกี่ยวกันถูกนำมาวัดระยะกัน ผลการค้นจะออกมาเหมือนสุ่ม")
    print("  แต่หน้าตาเป็นผลการค้นปกติทุกอย่าง")
    print()

    rule("วิธีตรวจสอบ")
    print("  ถามคำถามที่รู้คำตอบอยู่แล้วสักข้อ ถ้าคะแนนความคล้ายของอันดับ 1 ต่ำผิดปกติ")
    print("  และผลที่ได้ไม่เกี่ยวกับคำถามเลย ให้สงสัยเรื่องนี้ก่อนเรื่องคุณภาพคลัง")
    print()
    print("  แล้วเทียบ metadata ของ collection กับค่าที่ record บันทึกไว้ตรง ๆ")
    print()

    rule("แนวทางแก้")
    print("  บันทึก provider ลง metadata ของ collection แบบเดียวกับที่ทำกับ dimension")
    print("  แล้วเทียบตอนค้น เปลี่ยนการสันนิษฐานให้เป็นการตรวจสอบ")
    print()
    print("  ที่ทำแบบนี้ตั้งแต่แรกเพราะ dimension เป็นเรื่องที่ทำให้ upsert ล้มเหลว")
    print("  จึงเห็นทันที ส่วน provider ที่ผิดไม่ทำให้อะไรล้มเหลว มันแค่ทำให้ผลแย่ลง")
    print("  ซึ่งเป็นความล้มเหลวประเภทที่หาเจอยากกว่ามาก")


if __name__ == "__main__":
    run()
