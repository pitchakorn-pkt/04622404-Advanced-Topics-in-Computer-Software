# -*- coding: utf-8 -*-
# Problem 04: main.py shows one result and there is no reranking behind it
#
# config.TOP_K is 3. main.py:62 passes top_k=1 instead, with the line that would
# have used the configured value commented out directly above it. So the user
# sees the single nearest chunk and nothing else, and there is no second stage
# that could have reordered the candidates before that cut.

from _cases import SINGLE
from data_loader import get_retriever, head, rule

import config


def run():
    retriever = get_retriever()
    print()

    rule("ค่าที่ตั้งไว้ กับค่าที่ใช้จริง")
    print(f"  config.TOP_K            {config.TOP_K}")
    print("  main.py:61              # results = retriever.retrieve(query, top_k=config.TOP_K)")
    print("  main.py:62              results = retriever.retrieve(query, top_k=1)")
    print()
    print("  บรรทัดที่อ่านค่าจาก config ถูก comment ทิ้ง แล้วเขียนทับด้วยเลข 1 ตรง ๆ")
    print("  การแก้ TOP_K ใน config.py จึงไม่มีผลอะไรกับ main.py เลย")
    print()
    print("  ทั้งสองบรรทัดนี้มาจากโครงต้นฉบับของแล็บ ไม่ได้ถูกแก้ในงานชิ้นนี้")
    print("  โค้ดใน src/ กับ labs/ ทั้งหมดเหมือนต้นฉบับ ส่วนที่เป็นงานของโปรเจกต์นี้")
    print("  คือชุดข้อมูลอาหารไทย 90 คู่ ปัญหาที่เขียนไว้ในโฟลเดอร์นี้จึงเป็นปัญหา")
    print("  ของระบบตามที่มันเป็น ไม่ใช่รายการสิ่งที่ทำพลาดระหว่างทาง")
    print()

    rule("ราคาที่จ่ายเมื่อตัดเหลืออันดับเดียว")
    lost = 0
    for query, expected in SINGLE.items():
        hits = retriever.retrieve(query, top_k=config.TOP_K)
        normalized = query.replace(" ", "")
        position = None
        for rank, hit in enumerate(hits, start=1):
            if normalized in hit["question"].replace(" ", ""):
                position = rank
                break
        if position and position > 1:
            lost += 1
            print(f"  {head(query, 44)}")
            print(f"      อันดับ 1  {hits[0]['score']:.4f}  {head(hits[0]['question'], 40)}")
            print(f"      อันดับ {position}  {hits[position-1]['score']:.4f}  {head(hits[position-1]['question'], 40)}  <-- คู่ที่ตรงคำถาม")

    print()
    print(f"  จากคำถามเจาะจงเมนู {len(SINGLE)} ข้อ มี {lost} ข้อที่คู่ที่ตรงคำถามอยู่อันดับ 2-3")
    print("  ด้วย top_k=1 ผู้ใช้ไม่มีวันเห็นคู่พวกนั้น ทั้งที่ระบบค้นเจอแล้ว")
    print()
    print(f"  ระยะห่างของคะแนนในเคสข้างบนคือ 0.7448 กับ 0.7113 ต่างกัน 0.0335")
    print("  ซึ่งเล็กเกินกว่าจะถือว่าอันดับ 1 ดีกว่าอันดับ 2 อย่างมีความหมาย")
    print()

    rule("ไม่มีขั้นจัดอันดับใหม่มารองรับ")
    print("  ระบบนี้มีขั้นเดียว — encode คำถาม แล้วค้น FAISS (retriever.py:27-28)")
    print("  ไม่มี BM25 ไม่มี RRF ไม่มี cross-encoder")
    print()
    print("  bi-encoder เข้ารหัสคำถามกับเอกสารแยกกัน มันจึงเก่งเรื่อง 'พูดเรื่องเดียวกัน'")
    print("  แต่อ่อนเรื่อง 'อันไหนตอบคำถามนี้' ซึ่งเป็นสาเหตุที่เคสข้าวซอยพลาด —")
    print('  ทั้งสองคู่พูดเรื่องข้าวซอยเหมือนกัน คู่ที่ถามเรื่อง "ภาคไหน" จึงไม่ได้')
    print("  โดดเด่นกว่าในสายตาของโมเดล")
    print()
    print("  LAB04 เพิ่มขั้นนี้เข้าไปแล้ววัดผล: hit@1 ขยับจาก 0.6333 เป็น 0.9333")
    print("  โดยที่ hit@10 แทบไม่เปลี่ยน ซึ่งเป็นอาการเดียวกับที่เห็นที่นี่")
    print()

    rule("แนวทางแก้ เรียงตามความคุ้ม")
    print("  1. คืนค่า top_k ให้อ่านจาก config แล้วแสดงผลทั้งสามอันดับพร้อมคะแนน")
    print("     แก้บรรทัดเดียว ไม่ต้อง build ใหม่ ผู้ใช้เลือกเองได้ว่าอันไหนตรง")
    print()
    print("  2. เปิดบรรทัดที่แสดงคำถามที่ตรงกัน (main.py:31) ควบคู่ไปด้วย")
    print("     ไม่งั้นการแสดงสามอันดับจะกลายเป็นข้อความสามก้อนที่แยกไม่ออก")
    print()
    print("  3. เพิ่ม cross-encoder แบบ LAB04 — ได้ผลมากที่สุดแต่แพงที่สุด")
    print("     ต้องโหลดโมเดลเพิ่ม 2.2 GB และเวลาต่อคำถามเพิ่มราว 24 เท่า")


if __name__ == "__main__":
    run()
