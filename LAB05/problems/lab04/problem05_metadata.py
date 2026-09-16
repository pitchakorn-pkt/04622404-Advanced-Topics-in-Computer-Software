# -*- coding: utf-8 -*-
# Problem 05: every chunk carries a category, and nothing ever reads it
#
# document_loader.py parses "[หมวด: ...]" headings, text_splitter.py copies the
# value onto each chunk, and it is stored in vector_db/chunk_store.json for all
# 194 chunks. From there it goes nowhere: this script scans the retrieval path
# and shows that no file on it ever looks at the field.
#
# The cost is not an error message. It is a class of question the system cannot
# answer at all, and a class of confusion it has no way to resolve.

import os
import re

from data_loader import BASE_DIR, head, load_chunks, load_embeddings, rule

# ไฟล์ที่อยู่บนเส้นทางค้นหาจริง ตั้งแต่รับคำถามจนได้คำตอบ
RETRIEVAL_PATH = [
    "src/query_transform.py",
    "src/hybrid_retriever.py",
    "src/retriever.py",
    "src/rerankers.py",
    "src/vector_store.py",
    "src/generator.py",
    "src/prompt_templates.py",
    "src/rag_pipeline.py",
    "serve.py",
    "main.py",
]


def scan_for_category():
    """หาว่ามีไฟล์ไหนบนเส้นทางค้นหาอ่านฟิลด์ category บ้าง"""
    hits = []
    for rel in RETRIEVAL_PATH:
        path = os.path.join(BASE_DIR, rel)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                code = line.split("#")[0]
                if re.search(r"category", code):
                    hits.append((rel, line_no, line.strip()))
    return hits


def run():
    chunks = load_chunks()

    rule("สิ่งที่เก็บไว้ — ทุก chunk มีหมวดครบ")
    categories = {}
    for chunk in chunks:
        categories[chunk["category"]] = categories.get(chunk["category"], 0) + 1
    print(f"  {len(chunks)} chunk แบ่งเป็น {len(categories)} หมวด")
    for name, count in categories.items():
        print(f"    {count:>4}  {name}")
    print()

    rule("สิ่งที่ใช้จริง — ไม่มีไฟล์ไหนบนเส้นทางค้นหาอ่านฟิลด์นี้เลย")
    hits = scan_for_category()
    print(f"  สแกน {len(RETRIEVAL_PATH)} ไฟล์บนเส้นทาง query -> retrieve -> rerank -> generate")
    if not hits:
        print("  พบการอ้างถึง category: 0 แห่ง")
    else:
        for rel, line_no, text in hits:
            print(f"    {rel}:{line_no}  {head(text)}")
    print()
    print("  ที่อ่านฟิลด์นี้มีที่เดียวคือ evaluation/build_golden_set.py:141")
    print("  ซึ่งใช้กระจายข้อสอบให้ครบทุกหมวด ไม่เกี่ยวกับการค้นหาตอนใช้งานจริง")
    print()

    rule("ข้อความที่เอาไปทำ embedding ก็ไม่มีชื่อหมวดอยู่ในนั้น")
    sample = chunks[0]
    print(f"  หมวดของ chunk นี้ : {sample['category']}")
    print(f"  text ที่ถูก embed : {head(sample['text'], 62)}")
    in_text = sum(1 for c in chunks if c["category"] in c["text"])
    print()
    print(f"  chunk ที่มีชื่อหมวดปรากฏอยู่ใน text : {in_text} จาก {len(chunks)}")
    print("  text ประกอบจาก 'Question: ... Answer: ...' เท่านั้น (text_splitter.py:41)")
    print("  ชื่อหมวดจึงไม่มีผลต่อทั้ง dense และ BM25 — มันไม่ได้อยู่ในดัชนีทั้งสองตัว")
    print()

    rule("ผลที่ตามมา 1 — คำถามระดับหมวดตอบไม่ได้เลย")
    print("  คำถามอย่าง 'เรื่องมิจฉาชีพมีอะไรบ้าง' หรือ 'สรุปหมวดแบตให้หน่อย'")
    print("  ต้องการการกวาดทั้งหมวด แต่ระบบมีแค่การหาเพื่อนบ้านที่ใกล้ที่สุด k ชิ้น")
    print("  มันจะคืน chunk 3 ชิ้นที่ใกล้ที่สุดแล้วให้ LLM เขียนคำตอบราวกับว่านั่นคือทั้งหมด")
    print()

    rule("ผลที่ตามมา 2 — สับสนข้ามหมวดโดยไม่มีอะไรกั้น")
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

    print(f"  chunk ที่เพื่อนบ้านใกล้ที่สุดอยู่คนละหมวด: {len(crossing)} คู่")
    print()
    for score, i, j in crossing[:4]:
        print(f"  cosine {score:.4f}")
        print(f"      [{i:3}] {chunks[i]['category']:<28} {head(chunks[i]['question'], 40)}")
        print(f"      [{j:3}] {chunks[j]['category']:<28} {head(chunks[j]['question'], 40)}")
    print()
    print("  ถ้ามีการกรองด้วยหมวด คำถามที่รู้อยู่แล้วว่าเป็นเรื่องแบตจะไม่มีวันไปโดน")
    print("  chunk หมวดเลือกซื้อเครื่อง แต่ตอนนี้ไม่มีอะไรกั้น")
    print()

    rule("วิธีตรวจสอบ")
    print("  รันสคริปต์นี้ — ถ้าส่วน 'ใช้จริง' ยังพิมพ์ 0 แห่ง แปลว่าฟิลด์นี้ยังเป็นของตาย")
    print("  อีกทางคือ grep -rn category src/ แล้วดูว่ามีแต่บรรทัดที่ 'เขียน' ไม่มีที่ 'อ่าน'")
    print()

    rule("แนวทางแก้")
    print("  1. กรองก่อนค้น — เดาหมวดจากคำถามแล้วค้นเฉพาะ chunk ในหมวดนั้น")
    print("     ได้ผลชัดกับคลังที่หมวดแยกกันเด็ดขาด แต่คลังนี้หมวดคาบเกี่ยวกันเยอะ")
    print("     (ดูคู่ข้ามหมวดข้างบน) เดาผิดครั้งเดียวคือค้นไม่เจอเลย ไม่ใช่แค่อันดับตก")
    print()
    print("  2. ใส่ชื่อหมวดเข้าไปใน text ที่ embed — แก้บรรทัดเดียวที่ text_splitter.py:41")
    print("     ราคาถูกกว่าและไม่มีทางทำให้ค้นไม่เจอ แต่ต้อง build index ใหม่ทั้งชุด")
    print("     และต้องวัดใหม่ทั้งตาราง เพราะเวกเตอร์ทุกตัวเปลี่ยน")
    print()
    print("  ยังไม่ได้ทำทั้งสองข้อ เพราะตัวเลขที่รายงานไว้ทั้งหมดวัดบนดัชนีชุดปัจจุบัน")


if __name__ == "__main__":
    run()
