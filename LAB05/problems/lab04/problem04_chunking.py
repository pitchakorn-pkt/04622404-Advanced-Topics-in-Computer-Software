# -*- coding: utf-8 -*-
# Problem 04: the chunking stage never actually runs
#
# config.py sets CHUNK_SIZE = 400 with CHUNK_OVERLAP = 50, and build_index.py
# calls build_chunks() on every record. Measured on the committed corpus, the
# splitter has never once split anything: 194 records go in, 194 chunks come
# out, and the longest chunk is 392 characters — eight characters below the
# threshold that would trigger a split.
#
# So the overlap setting has no effect on this system at all, and the tuning
# written into config.py describes a stage that is inert.

from data_loader import head, load_chunks, load_records, rule

import config
from src.text_splitter import split_text

# ข้อความยาวเกินเกณฑ์ ใช้ดูว่าถ้ามีคำตอบยาว ๆ จริงจะถูกตัดยังไง
LONG_ANSWER = (
    "ขั้นแรกให้สำรองข้อมูลก่อนเสมอเพราะขั้นตอนถัดไปมีโอกาสทำให้ข้อมูลหาย "
    "จากนั้นเข้าไปที่หน้าตั้งค่าแล้วเลือกหัวข้อพื้นที่เก็บข้อมูลเพื่อดูว่าอะไรกินที่มากที่สุด "
    "ถ้าเป็นรูปและวิดีโอให้ย้ายขึ้นคลาวด์แล้วลบต้นฉบับในเครื่องออกทีละชุด "
    "ถ้าเป็นแอปให้ดูว่าแอปไหนไม่ได้เปิดเลยเกินสามเดือนแล้วถอนออกก่อน "
    "สุดท้ายให้ล้างแคชของเบราว์เซอร์และแอปแชตซึ่งมักโตขึ้นเรื่อย ๆ โดยไม่มีใครสังเกต "
    "แล้วรีสตาร์ตเครื่องหนึ่งครั้งเพื่อให้ระบบคืนพื้นที่ชั่วคราวที่จองไว้"
)


def run():
    records = load_records()
    chunks = load_chunks()
    lengths = [len(c["text"]) for c in chunks]
    split_chunks = [c for c in chunks if c["part_idx"] > 0]

    rule("อาการ — ขั้นแบ่ง chunk ไม่เคยทำงานเลยสักครั้ง")
    print(f"  CHUNK_SIZE ที่ตั้งไว้     {config.CHUNK_SIZE} ตัวอักษร")
    print(f"  CHUNK_OVERLAP ที่ตั้งไว้  {config.CHUNK_OVERLAP} ตัวอักษร")
    print()
    print(f"  record เข้า              {len(records)}")
    print(f"  chunk ออก               {len(chunks)}")
    print(f"  chunk ที่ part_idx > 0    {len(split_chunks)}   <-- ศูนย์ = ไม่มีชิ้นไหนถูกแบ่ง")
    print()
    print(f"  ความยาว chunk: สั้นสุด {min(lengths)}  ยาวสุด {max(lengths)}  เฉลี่ย {sum(lengths)/len(lengths):.1f}")
    print(f"  ห่างจากเกณฑ์ {config.CHUNK_SIZE} อยู่ {config.CHUNK_SIZE - max(lengths)} ตัวอักษร")
    print()

    rule("สาเหตุ")
    print("  split_text() คืนข้อความทั้งก้อนทันทีถ้าสั้นกว่าเกณฑ์ (text_splitter.py:19-20)")
    print("  ส่วน build_chunks() ประกอบข้อความเป็น 'Question: ... Answer: ...' ต่อ 1 คู่")
    print("  ถาม-ตอบ (text_splitter.py:41) ซึ่งคลังนี้ยาวไม่ถึง 400 สักคู่เดียว")
    print()
    print("  ผลคือ CHUNK_OVERLAP = 50 ไม่มีผลอะไรกับระบบนี้เลย และคอมเมนต์ปรับจูน")
    print("  ที่เขียนไว้ใน config.py:56-58 อธิบายขั้นตอนที่ไม่ได้ทำงานจริง")
    print()

    rule("ทำไมถึงยังไม่ใช่บั๊ก แต่เป็นความเสี่ยง")
    print(f"  ยาวสุดตอนนี้คือ {max(lengths)} ห่างเพดานแค่ {config.CHUNK_SIZE - max(lengths)} ตัวอักษร")
    print("  เติมคำตอบที่ยาวกว่านี้เข้าไปเพียงข้อเดียว ขั้นแบ่งจะเริ่มทำงานทันที")
    print("  โดยไม่มีใครสังเกต และมันแบ่งด้วยการนับตัวอักษรล้วน ไม่ดูขอบเขตประโยค")
    print()
    print(f"  ลองกับคำตอบยาว {len(LONG_ANSWER)} ตัวอักษร:")
    pieces = split_text(LONG_ANSWER, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    for i, piece in enumerate(pieces):
        print(f"    ชิ้นที่ {i}  ({len(piece)} ตัวอักษร)")
        print(f"      ขึ้นต้น : {head(piece, 58)}")
        print(f"      ลงท้าย : ...{piece[-46:]}")
    print()
    print("  ชิ้นแรกจบกลางคำ ส่วนชิ้นที่สองขึ้นต้นกลางคำเช่นกัน เวลาเอาไปทำ embedding")
    print("  เศษคำพวกนี้จะกลายเป็นสัญญาณรบกวน และเวลาส่งให้ LLM ก็อ่านไม่รู้เรื่อง")
    print()

    rule("วิธีตรวจสอบ")
    print("  รันสคริปต์นี้ทุกครั้งที่แก้คลังหรือแก้ CHUNK_SIZE แล้วดูสองบรรทัด:")
    print("    - chunk ที่ part_idx > 0  ถ้ายังเป็น 0 แปลว่าขั้นนี้ยังไม่ทำงาน")
    print("    - ความยาวสูงสุด          ถ้าเข้าใกล้ CHUNK_SIZE แปลว่ากำลังจะเริ่มทำงาน")
    print()

    rule("แนวทางแก้")
    print("  ทางเลือกที่ตรงกับคลังนี้ที่สุดคือไม่แบ่งเลย แล้วลบการตั้งค่าที่ไม่มีผลออก")
    print("  เพราะ 1 คู่ถาม-ตอบ = 1 หน่วยความหมายที่สมบูรณ์อยู่แล้ว การแบ่งมีแต่จะทำลาย")
    print()
    print("  ถ้าจะเก็บขั้นนี้ไว้เผื่อคลังโตขึ้น ควรแบ่งตามขอบเขตประโยคแทนการนับตัวอักษร")
    print("  และควรให้ build_index.py พิมพ์จำนวนชิ้นที่ถูกแบ่งจริงออกมาทุกครั้ง")
    print("  ตอนนี้บรรทัดที่พิมพ์จำนวน chunk ถูก comment ทิ้งไว้ (build_index.py:51)")
    print("  จึงไม่มีสัญญาณอะไรบอกเลยว่าขั้นนี้ทำอะไรไปบ้าง")


if __name__ == "__main__":
    run()
