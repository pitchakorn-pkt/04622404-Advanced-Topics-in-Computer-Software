# -*- coding: utf-8 -*-
# Problem 08: settings that look like tuning knobs but change what the system is
#
# config.py is one file of flags. Four of them have bitten this project: a
# weight that is not universal, a model name that went away, a display switch
# that hides work already done, and a stage whose default quietly disables a
# feature elsewhere. The index freshness check is run live at the end.

from data_loader import rule

import config
from src import index_meta

# ตารางที่วัดเองบน variant paraphrase (บันทึกไว้ใน config.py:82-87)
WEIGHT_TABLE = [
    ("1 : 0", 0.8961, 0.9482, "ไม่ใช้ BM25 เลย"),
    ("1 : 0.5", 0.7219, 0.9482, "ค่าที่ใช้อยู่"),
    ("1 : 1", 0.6967, 0.9496, "ค่าดั้งเดิมของสูตร RRF"),
    ("1 : 1.5", 0.6165, 0.7583, ""),
    ("0 : 1", 0.4953, 0.7583, "BM25 อย่างเดียว"),
]


def run():
    rule("1. น้ำหนักผสมไม่ใช่ค่าสากล — ต้องวัดกับคลังของตัวเอง")
    print(f"  {'dense : BM25':<14}{'ปิด rerank':>12}{'เปิด rerank':>13}   หมายเหตุ")
    for weights, off, on, note in WEIGHT_TABLE:
        print(f"  {weights:<14}{off:>12.4f}{on:>13.4f}   {note}")
    print()
    print(f"  ค่าที่ตั้งไว้ตอนนี้: DENSE_WEIGHT = {config.DENSE_WEIGHT}  BM25_WEIGHT = {config.BM25_WEIGHT}")
    print()
    print("  อ่านคอลัมน์ 'ปิด rerank' จากบนลงล่าง — ยิ่งให้น้ำหนัก BM25 มาก ยิ่งแย่ลง")
    print("  ทุกขั้น การผสมสองวิธีจึงไม่ได้ดีกว่าเสมอไป คลังนี้คำถามกับคำตอบแทบไม่มี")
    print("  คำหายากที่ตรงกันเป๊ะ BM25 จึงอ่อน และถ้าถ่วงเท่ากันมันจะลากผลรวมลง")
    print()
    print("  คลังที่มีรหัสรุ่น เลขพาร์ต หรือชื่อเฉพาะเยอะจะให้ผลกลับกัน")
    print("  ค่านี้จึงต้องวัดใหม่ทุกครั้งที่เปลี่ยนคลัง ห้ามลอกมาจากที่อื่น")
    print()
    print("  ข้อสังเกตที่ทำให้ไม่ตั้งเป็น 0 ไปเลย: เมื่อเปิด rerank ค่าในช่วง 0 ถึง 1")
    print("  ให้ผลเท่ากันทุกข้อ เพราะตัวจัดอันดับใหม่เรียงผู้เข้ารอบใหม่ทั้งชุดอยู่แล้ว")
    print("  ค่านี้จึงมีผลจริงเฉพาะตอนปิด rerank")
    print()

    rule("2. ชื่อโมเดลที่ผู้ให้บริการถอดออก แล้วระบบไม่ฟ้อง")
    provider = config.LLM_PROVIDER
    base_url, default_model, key_name = config.LLM_PROVIDERS[provider]
    print(f"  LLM_PROVIDER            {provider}")
    print(f"  LLM_MODEL               {config.LLM_MODEL!r}")
    print(f"  ค่าเริ่มต้นของผู้ให้บริการ {default_model!r}")
    print()
    print("  generator.py:23 เขียนว่า  self.model = config.LLM_MODEL or default_model")
    print(f"  ถ้า LLM_MODEL ว่างเมื่อไหร่ ระบบจะถอยไปใช้ {default_model!r}")
    print("  ซึ่ง Groq ถอดออกไปแล้วตั้งแต่ 18 ส.ค. 2026 — ค่าเริ่มต้นในตารางนี้จึงตายแล้ว")
    print()
    print("  อาการเวลาโมเดลใช้ไม่ได้: get_llm() ดัก exception แล้วคืน NoLLM")
    print("  (generator.py:69-74) ระบบยังตอบได้ปกติ แต่คำตอบกลายเป็นข้อความดิบจากคลัง")
    print("  ไม่มี error ให้เห็นเลย")
    print()
    print("  วิธีตรวจ: grep คำตอบที่ได้ในไฟล์คลัง ถ้าเจอตรงตัว = LLM ไม่ได้ทำงาน")
    print("  หรือดูบรรทัด [llm] Failed to use ... ใน log")
    print("  บทเรียน: ก่อนเดโมทุกครั้งต้องยืนยันว่า LLM ทำงานจริง")
    print("  อย่าดูแค่ว่ามีคำตอบออกมา")
    print()

    rule("3. สวิตช์แสดงผลที่ปิดงานที่ทำเสร็จแล้วทิ้ง")
    print(f"  SHOW_SOURCES = {config.SHOW_SOURCES}")
    print()
    print("  generator.build_sources() (generator.py:113-123) ประกอบรายการแหล่งอ้างอิง")
    print("  พร้อมเลข chunk_id คำถาม บรรทัดต้นทาง และคะแนน — ทำงานทุกครั้งที่ตอบ")
    print("  แล้ว main.py ไม่พิมพ์ออกมาเพราะสวิตช์นี้ปิดอยู่")
    print()
    print("  ผู้ใช้จึงเห็นเลข [1] [2] ในคำตอบ แต่ไม่มีทางรู้ว่า [1] คืออะไร")
    print("  ซึ่งย้อนแย้งกับเหตุผลทั้งหมดของการบังคับให้อ้างอิง")
    print()

    rule("4. ค่าเริ่มต้นของขั้นหนึ่ง ปิดความสามารถของอีกขั้นโดยไม่มีใครบอก")
    print(f"  USE_QUERY_TRANSFORM = {config.USE_QUERY_TRANSFORM}")
    print(f"  USE_MEMORY          = {config.USE_MEMORY}")
    print()
    print("  ประวัติบทสนทนาถูกส่งให้ตัวปรับคำถามได้เฉพาะตอน USE_QUERY_TRANSFORM เปิด")
    print("  (rag_pipeline.py:61-62) ซึ่งค่าเริ่มต้นปิดไว้")
    print()
    print("  ผลคือ USE_MEMORY = True มีผลแค่ตอนเขียนคำตอบ ไม่มีผลตอนค้น")
    print('  คำถามต่อเนื่องอย่าง "แล้วอันไหนดีกว่ากัน" จึงถูกเอาไปค้นทั้งอย่างนั้น')
    print("  แล้วได้เอกสารคนละเรื่อง")
    print()
    print("  ลองแก้ด้วยการเติมคำถามก่อนหน้าเข้าไปแล้ววัด 2 แบบ ไม่มีแบบไหนดีขึ้น")
    print("  จึงคงพฤติกรรมเดิมไว้ และเขียนข้อจำกัดนี้ลง README แทนที่จะปล่อยเงียบ")
    print()

    rule("5. ตรวจว่า index ตรงกับคลังปัจจุบันไหม (รันสด)")
    meta = index_meta.get_current_state()
    print(f"  ไฟล์คลัง  {config.SOURCE_FILE.split('/')[-1]}")
    print(f"  ขนาด      {meta['file']['size']} ไบต์")
    print(f"  sha256    {meta['file']['sha256'][:32]}...")
    print(f"  ค่าที่ผูกไว้ {meta['settings']}")
    print()
    problems = index_meta.find_problems()
    if problems:
        for p in problems:
            print(f"  ! {p}")
        print("  -> ต้องรัน python build_index.py ใหม่")
    else:
        print("  index ตรงกับคลังและค่าตั้งปัจจุบัน")
    print()
    print("  เดิมตัวนี้เทียบด้วยเวลาแก้ไขไฟล์ (mtime) ซึ่ง git ตั้งใหม่ทุกครั้งที่ checkout")
    print("  ใครก็ตามที่ clone repo มาจึงโดนเตือนว่า index ล้าสมัยทันที ทั้งที่เนื้อไฟล์")
    print("  เหมือนเดิมทุกไบต์ แก้เป็น sha256 ของเนื้อไฟล์แล้ว (index_meta.py:22-34)")


if __name__ == "__main__":
    run()
