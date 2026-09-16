# -*- coding: utf-8 -*-
# Problem 06: an answer that cites a posting which does not exist
#
# Every claim in an answer has to carry the tag of the passage it came from.
# A model that writes the tag correctly except for one character produces an
# answer that reads perfectly and points at nothing. The check that catches it
# is the one place in this pipeline where "looks right" is not good enough.

import os
import re

from data_loader import PIPELINE, head, rule

VECTOR_SRC = os.path.join(PIPELINE, "vector_store.py")
_SOURCE = open(VECTOR_SRC, encoding="utf-8").read()

# ดึงรูปแบบป้ายอ้างอิงและฟังก์ชันตรวจออกมาจากไฟล์จริง แทนการ import ทั้งโมดูล
# (vector_store.py import chromadb ตอนโหลด ซึ่งไม่ได้ติดตั้งไว้ใน venv นี้)
CITATION_PATTERN = re.compile(
    re.search(r"^CITATION_PATTERN = re\.compile\(r\"(.+)\"\)$", _SOURCE, re.M).group(1)
)
_namespace = {"CITATION_PATTERN": CITATION_PATTERN}
exec(re.search(r"^def cited_tags\(.*?(?=^\S|\Z)", _SOURCE, re.S | re.M).group(), _namespace)
cited_tags = _namespace["cited_tags"]

# passage ที่ส่งให้โมเดล — id ของ AIDevBoard เป็น UUID
OFFERED = {
    ("aidevboard_ai", "48720738-0f4b-483d-9739-14039ae457d0", 0),
    ("jobicy_software_en", "147496", 2),
}

# คำตอบสามแบบ: อ้างถูก, อ้าง UUID ผิดหนึ่งตัวอักษร, ไม่อ้างเลย
ANSWERS = {
    "อ้างอิงถูกต้อง": (
        "Canonical is hiring for Kubernetes work "
        "[jobicy_software_en:147496#2] and one AI board role also lists it "
        "[aidevboard_ai:48720738-0f4b-483d-9739-14039ae457d0#0]."
    ),
    "UUID ผิดหนึ่งตัวอักษร": (
        "Canonical is hiring for Kubernetes work "
        "[jobicy_software_en:147496#2] and one AI board role also lists it "
        "[aidevboard_ai:48720738-0f4b-483d-9739-14039ae457d1#0]."
    ),
    "ไม่ใส่ป้ายอ้างอิงเลย": (
        "Canonical is hiring for Kubernetes work, and one AI board role lists it too."
    ),
}


def run():
    rule("รูปแบบป้ายอ้างอิงที่ระบบบังคับ")
    print(f"  {CITATION_PATTERN.pattern}")
    print("  เช่น  [jobicy_software_en:147496#2]  =  แหล่ง : id ของประกาศ # ลำดับ chunk")
    print()
    print("  รูปแบบเดียวกันนี้ถูกใช้สองที่ — เขียนลงคำสั่งที่ส่งให้โมเดล และใช้ตรวจ")
    print("  สิ่งที่โมเดลเขียนกลับมา (vector_store.py:97-104) จึงไม่มีทางหลุดจากกัน")
    print()

    rule("passage ที่ถูกส่งให้โมเดลในตัวอย่างนี้")
    for source, ident, index in sorted(OFFERED):
        print(f"  [{source}:{ident}#{index}]")
    print()

    rule("ตรวจคำตอบสามแบบด้วยฟังก์ชันจริง")
    for label, text in ANSWERS.items():
        used = cited_tags(text)
        invented = sorted(used - OFFERED)
        citations = sorted(used & OFFERED)
        verdict = "ผ่าน" if not invented else "จับได้"
        print(f"  {verdict}  {label}")
        print(f"        อ้างถูกต้อง {len(citations)}  แต่งขึ้นเอง {len(invented)}")
        for source, ident, index in invented:
            print(f"        แต่งขึ้น: [{source}:{ident}#{index}]")
        print()

    rule("ทำไมเคสที่สองถึงอันตรายที่สุด")
    print("  คำตอบอ่านแล้วสมบูรณ์ ป้ายอ้างอิงถูกรูปแบบทุกอย่าง แหล่งถูก ลำดับ chunk ถูก")
    print("  ผิดแค่ตัวอักษรสุดท้ายของ UUID จาก ...457d0 เป็น ...457d1")
    print()
    print("  คนอ่านไม่มีทางเห็น UUID ยาว 36 ตัวอักษรและไม่มีใครไล่ตรวจทีละตัว")
    print("  ถ้าไม่มีการตรวจอัตโนมัติ คำตอบนี้จะผ่านไปในฐานะคำตอบที่ดี")
    print("  แล้วชี้ไปยังประกาศที่ไม่มีอยู่จริง")
    print()
    print("  ส่วนเคสที่สามที่ไม่ใส่ป้ายเลย 'ผ่าน' การตรวจนี้ เพราะมันตรวจแค่ว่า")
    print("  ป้ายที่เขียนมามีอยู่จริงไหม ไม่ได้ตรวจว่าเขียนป้ายครบทุกข้ออ้างหรือเปล่า")
    print("  นั่นเป็นช่องที่ยังเปิดอยู่")
    print()

    rule("การตัดสินใจที่ตามมา — เลือกโมเดลใหญ่เป็นค่าเริ่มต้น")
    for line in _SOURCE.splitlines():
        if "llama-3.1-8b" in line or "DEFAULT_LLM_MODEL =" in line:
            print(f"    {head(line.strip(), 66)}")
    print()
    print("  llama-3.1-8b-instant ถูกจับได้ว่าคัดลอก UUID ผิดหนึ่งตัวอักษรจริง")
    print("  ระหว่างทดสอบสี่คำถาม การตรวจจับมันได้ แต่ข้อสรุปคือ")
    print("  'ป้ายอ้างอิงที่ต้องคอยจับ ไม่คุ้มกับความเร็วที่ได้'")
    print("  จึงเปลี่ยนค่าเริ่มต้นเป็นโมเดลใหญ่ และเก็บตัวเล็กไว้ให้เลือกด้วย --model")
    print()
    print("  นี่คือกรณีที่ตัววัดผลเปลี่ยนการออกแบบ ไม่ใช่แค่รายงานตัวเลข")
    print()

    rule("วิธีตรวจสอบ")
    print("  ดูค่า invented ในผลลัพธ์ของ answer() ทุกครั้ง ถ้าไม่ว่างแปลว่าโมเดล")
    print("  เขียนป้ายที่ไม่ได้ถูกส่งให้ ซึ่งไม่ควรเกิดขึ้นเลยสักครั้ง")
    print()
    print("  ถ้าเกิดบ่อยกับโมเดลไหน ให้เปลี่ยนโมเดล ไม่ใช่ปรับ prompt —")
    print("  ความสามารถในการคัดลอกสตริงยาวให้ตรงเป๊ะเป็นเรื่องของตัวโมเดล")


if __name__ == "__main__":
    run()
