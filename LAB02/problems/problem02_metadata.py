# -*- coding: utf-8 -*-
# Problem 02: the menu name is stored on every chunk and never used
#
# The corpus is 15 menus with 6 Q&A pairs each, and the menu name is the
# category. It reaches the chunk store and stops there: nothing filters by it,
# nothing embeds it, and main.py has the line that would show it commented out.

import os
import re

from data_loader import BASE_DIR, head, load_chunks, load_embeddings, rule

RETRIEVAL_PATH = ["src/retriever.py", "src/embedding_model.py", "src/vector_store.py", "main.py"]


def scan_for_category():
    """หาว่ามีบรรทัดไหนบนเส้นทางค้นหาที่อ้างถึง category บ้าง แยกโค้ดกับคอมเมนต์"""
    live, commented = [], []
    for rel in RETRIEVAL_PATH:
        path = os.path.join(BASE_DIR, rel)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                if "category" not in line:
                    continue
                (commented if line.strip().startswith("#") else live).append((rel, line_no, line.strip()))
    return live, commented


def run():
    chunks = load_chunks()

    rule("สิ่งที่เก็บไว้")
    categories = {}
    for chunk in chunks:
        categories[chunk["category"]] = categories.get(chunk["category"], 0) + 1
    print(f"  {len(chunks)} chunk แบ่งเป็น {len(categories)} หมวด หมวดละ {min(categories.values())}-{max(categories.values())} ข้อ")
    print(f"  หมวดคือชื่อเมนู: {', '.join(list(categories)[:6])} …")
    print()

    rule("สิ่งที่ใช้จริง")
    live, commented = scan_for_category()
    print(f"  สแกน {len(RETRIEVAL_PATH)} ไฟล์บนเส้นทางค้นหา")
    print(f"    บรรทัดที่ทำงานจริง : {len(live)}")
    print(f"    บรรทัดที่ถูก comment : {len(commented)}")
    print()
    for rel, line_no, text in commented:
        print(f"    {rel}:{line_no}  {head(text, 58)}")
    print()
    print("  ไม่มีบรรทัดไหนที่ทำงานจริงอ่านฟิลด์นี้เลย ตัวที่มีถูก comment ทิ้ง")
    print("  ผู้ใช้จึงเห็นแค่ข้อความคำตอบ ไม่รู้ว่ามาจากเมนูไหนและตรงกับคำถามไหน")
    print()
    print("  บรรทัดที่ถูก comment มาจากโครงต้นฉบับของแล็บ ไม่ได้ถูกแก้ในงานชิ้นนี้")
    print()

    in_text = sum(1 for c in chunks if c["category"] in c["text"])
    rule("ชื่อเมนูอยู่ในข้อความที่ embed หรือเปล่า")
    print(f"  chunk ที่มีชื่อหมวดของตัวเองอยู่ใน text : {in_text} จาก {len(chunks)}")
    print()
    print("  ที่นับได้ไม่ใช่ศูนย์เพราะคำถามส่วนใหญ่เอ่ยชื่อเมนูอยู่แล้วโดยธรรมชาติ")
    print('  เช่น "ต้มยำกุ้งใส่อะไรบ้าง" ชื่อเมนูจึงเข้าไปในดัชนีโดยบังเอิญ ไม่ใช่โดยออกแบบ')
    print()
    missing = [c for c in chunks if c["category"] not in c["text"]]
    print(f"  ส่วนอีก {len(missing)} ชิ้นที่ไม่ตรง เป็นเพราะข้อความใช้ชื่อแบบย่อ:")
    for chunk in missing[:3]:
        print(f"    หมวด {chunk['category']:<18} แต่ข้อความเขียนว่า {head(chunk['question'], 34)}")
    print()
    print("  ทั้งสองกรณีบอกเรื่องเดียวกัน — การที่ชื่อเมนูอยู่ในดัชนีเป็นผลข้างเคียง")
    print("  ของวิธีเขียนคำถาม ไม่ใช่สิ่งที่ระบบจัดการ ระบบจึงพึ่งมันไม่ได้")
    print()

    rule("ผลที่ตามมา — สับสนข้ามเมนูโดยไม่มีอะไรกั้น")
    import numpy as np

    vectors = load_embeddings()
    similarity = vectors @ vectors.T
    np.fill_diagonal(similarity, -1)
    crossing = []
    for i in range(len(chunks)):
        j = int(similarity[i].argmax())
        if i < j and chunks[i]["category"] != chunks[j]["category"]:
            crossing.append((float(similarity[i][j]), i, j))
    crossing.sort(reverse=True)

    print(f"  chunk ที่เพื่อนบ้านใกล้ที่สุดอยู่คนละเมนู: {len(crossing)} คู่")
    print()
    for score, i, j in crossing[:4]:
        print(f"  cosine {score:.4f}")
        print(f"      [{chunks[i]['category']}] {head(chunks[i]['question'], 46)}")
        print(f"      [{chunks[j]['category']}] {head(chunks[j]['question'], 46)}")
    print()
    print("  คำถามหกแบบซ้ำกันทั้ง 15 เมนู (ใส่อะไรบ้าง / ภาคไหน / เผ็ดไหม / ทำยังไง …)")
    print("  โครงประโยคจึงเหมือนกันหมด ต่างกันแค่ชื่อเมนู ซึ่งเป็นคำสั้น ๆ คำเดียว")
    print("  นี่คือคลังที่การกรองด้วยหมวดจะช่วยได้มากที่สุด และเป็นคลังที่ไม่ได้ใช้มันเลย")
    print()

    rule("แนวทางแก้")
    print("  1. เปิดบรรทัดที่ถูก comment ใน main.py ให้แสดงเมนูและคำถามที่ตรงกัน")
    print("     แก้ได้ทันที ไม่ต้อง build ใหม่ และทำให้ผู้ใช้ตรวจสอบคำตอบเองได้")
    print()
    print("  2. เติมชื่อเมนูเข้าไปใน text ที่ embed ตอนสร้าง chunk")
    print("     ต้อง build ดัชนีใหม่ และต้องวัดผลใหม่ทั้งชุด")
    print()
    print("  3. กรองด้วยเมนูเมื่อคำถามเอ่ยชื่อเมนูตรง ๆ — คลังนี้เมนูแยกกันเด็ดขาด")
    print("     ความเสี่ยงจากการเดาผิดจึงต่ำกว่าคลังของ LAB04 มาก")


if __name__ == "__main__":
    run()
