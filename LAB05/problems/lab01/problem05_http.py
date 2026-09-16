# -*- coding: utf-8 -*-
# Problem 05: three ways a remote call fails without saying anything useful
#
# The pipeline speaks HTTP through urllib alone, with no requests dependency.
# That is a deliberate choice and it costs three things, all of which were hit
# during development and two of which are fixed in the code as it stands.

import os
import re

from data_loader import PIPELINE, rule

EMBEDDING_SRC = os.path.join(PIPELINE, "embedding.py")
VECTOR_SRC = os.path.join(PIPELINE, "vector_store.py")

# โมเดลที่ Groq ถอดออกไปแล้ว พบตอนทำ LAB04 เมื่อ 18 ส.ค. 2026
WITHDRAWN = "llama-3.3-70b-versatile"


def show(path, pattern, label, context=0):
    """พิมพ์บรรทัดในไฟล์จริงที่ตรงกับ pattern พร้อมเลขบรรทัด"""
    name = os.path.basename(path)
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    hits = [i for i, line in enumerate(lines) if re.search(pattern, line)]
    print(f"  {label}")
    for i in hits[:3]:
        for j in range(i, min(i + 1 + context, len(lines))):
            print(f"    {name}:{j+1:<4} {lines[j].rstrip()}")
    if not hits:
        print(f"    (ไม่พบใน {name})")
    print()
    return hits


def run():
    rule("1. Cloudflare ปฏิเสธ User-Agent ของ urllib")
    print("  urllib ประกาศตัวเองว่า Python-urllib/3.x ซึ่ง Cloudflare ปฏิเสธทันที")
    print("  บาง endpoint ตอบกลับเป็น HTTP 403 พร้อมข้อความ error code: 1010")
    print("  โดยที่คำขอยังไปไม่ถึง API ด้วยซ้ำ")
    print()
    print("  สิ่งที่ทำให้หายาก: 403 อ่านเหมือน 'key ไม่มีสิทธิ์' ซึ่งเป็นสาเหตุแรก")
    print("  ที่ทุกคนจะไปไล่ ทั้งที่เรื่องนี้ไม่เกี่ยวกับ key เลย และ Groq ตอบ 403")
    print("  ไม่ใช่ 404 ทำให้ยิ่งดูเหมือนปัญหาสิทธิ์เข้าไปอีก")
    print()
    show(EMBEDDING_SRC, r"^USER_AGENT", "แก้แล้ว — ประกาศชื่อผู้เรียกไปตรง ๆ")
    show(EMBEDDING_SRC, r'headers = \{"User-Agent"', "และใส่ไปกับทุกคำขอ")

    rule("2. ตัวลองใหม่ที่ทิ้งเนื้อความของคำตอบ")
    print("  post_with_retry() เดิมจับ HTTPError แล้วรายงานแค่รหัสสถานะ")
    print("  ความล้มเหลวทุกแบบจึงหน้าตาเหมือนกันหมดจากข้างนอก และข้อความที่")
    print("  บอกสาเหตุจริง — อย่าง error code: 1010 ในข้อ 1 — ถูกทิ้งไปพร้อมกัน")
    print()
    show(EMBEDDING_SRC, r"detail = error\.read\(\)", "แก้แล้ว — อ่านเนื้อความออกมาด้วย")
    show(EMBEDDING_SRC, r"^RETRY_STATUS", "และแยกว่าสถานะไหนควรลองใหม่")
    print("  429 อยู่ในชุดที่ลองใหม่ เพราะ Gemini free tier วัดโควตาเป็นโทเคนต่อนาที")
    print("  และตอบ 429 ให้ทั้ง batch เมื่อหน้าต่างนั้นเต็ม — เป็นความล้มเหลวชั่วคราว")
    print("  ที่รอแล้วหายเอง ต่างจาก 403 ที่รอไปก็ไม่หาย")
    print()

    rule("3. ชื่อโมเดลที่ผู้ให้บริการถอดออก — ยังไม่ได้แก้")
    hits = show(VECTOR_SRC, r"^DEFAULT_LLM_MODEL", "ค่าที่ตั้งไว้ตอนนี้")
    if hits:
        print(f"  Groq ถอด {WITHDRAWN} ออกไปแล้วเมื่อ 18 ส.ค. 2026")
        print("  (พบตอนทำ LAB04 ซึ่งใช้ผู้ให้บริการเดียวกัน และแก้ config ที่นั่นแล้ว)")
        print()
    print("  อาการที่จะเจอ: คำขอถูกปฏิเสธเพราะชื่อโมเดล ไม่ใช่เพราะ key หรือโควตา")
    print("  ซึ่งอ่านจากรหัสสถานะอย่างเดียวแยกไม่ออก — ข้อ 2 คือสิ่งที่ทำให้แยกออก")
    print()
    print("  โค้ดเตือนเรื่องนี้ไว้แล้วที่ vector_store.py:74-76 ว่าให้เช็ครายชื่อโมเดล")
    print("  ที่ console.groq.com/docs/models ก่อนเปลี่ยน แต่รายชื่อนั้นเปลี่ยนได้เอง")
    print("  โดยที่โค้ดไม่รู้ ค่าคงที่ที่ชี้ไปยังของนอกระบบจึงหมดอายุได้เสมอ")
    print()

    rule("บทเรียนร่วมของทั้งสามข้อ")
    print("  ความล้มเหลวของการเรียกข้ามเครือข่ายมาถึงในรูปของตัวเลขสามหลัก")
    print("  ซึ่งบอกน้อยเกินกว่าจะไล่หาสาเหตุได้ สิ่งที่บอกได้อยู่ในเนื้อความ")
    print("  ที่มากับมัน การทิ้งเนื้อความนั้นจึงแพงกว่าที่คิดเสมอ")
    print()
    print("  และการแก้ข้อ 2 คือสิ่งที่ทำให้ข้อ 1 กับข้อ 3 หาเจอได้ในเวลาอันสั้น")


if __name__ == "__main__":
    run()
