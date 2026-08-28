# -*- coding: utf-8 -*-
# Problem 05: the system has no way to say the corpus does not cover this
#
# There is no score threshold anywhere in LAB02. FAISS always returns its
# nearest neighbours, so main.py always has something to print. The branch that
# would have said otherwise is unreachable.

from _cases import AGGREGATE, SINGLE
from data_loader import get_retriever, head, rule

OUT_OF_SCOPE = [
    "พาสต้าคาโบนาราทำยังไง",
    "ราคาตั๋วเครื่องบินไปเชียงใหม่",
    "สวัสดีครับ",
    "2+2 เท่ากับเท่าไหร่",
]


def run():
    retriever = get_retriever()
    print()

    rule("คำถามที่คลังไม่มีเรื่องนี้เลย")
    outside = []
    for query in OUT_OF_SCOPE:
        top = retriever.retrieve(query, top_k=1)[0]
        outside.append(top["score"])
        print(f"  {head(query, 32):<34} {top['score']:.4f}  [{top['category']}] {head(top['question'], 26)}")
    print()
    print("  ทุกข้อได้คำตอบกลับมา ไม่มีข้อไหนถูกปฏิเสธ")
    print()

    rule("เทียบกับคำถามที่คลังตอบได้จริง")
    inside = []
    for query in SINGLE:
        top = retriever.retrieve(query, top_k=1)[0]
        inside.append(top["score"])
    aggregate = []
    for query in AGGREGATE:
        top = retriever.retrieve(query, top_k=1)[0]
        aggregate.append(top["score"])

    def span(name, scores):
        print(f"  {name:<26} ต่ำสุด {min(scores):.4f}  สูงสุด {max(scores):.4f}")

    span("คำถามเจาะจงเมนู", inside)
    span("คำถามที่ต้องรวมหลายเมนู", aggregate)
    span("คำถามนอกคลัง", outside)
    print()

    gap = min(inside) - max(outside)
    if gap > 0:
        print(f"  ช่วงคะแนนของสองกลุ่มนี้ไม่ทับกัน ห่างกัน {gap:.4f}")
        print(f"  เกณฑ์ตัดที่ราว {(min(inside)+max(outside))/2:.2f} จะแยกออกได้ทั้งหมดในตัวอย่างชุดนี้")
    else:
        print(f"  ช่วงคะแนนทับกัน {abs(gap):.4f} — ไม่มีเกณฑ์ตัดค่าเดียวที่แยกสองกลุ่มนี้ออกได้")
    print()
    print("  คำถามที่ต้องรวมหลายเมนูเป็นกลุ่มที่ยากที่สุด มันอยู่ในโดเมนจริง")
    print("  คะแนนจึงไม่ต่ำ แต่คำตอบที่ได้ก็ไม่ถูก เกณฑ์ตัดค่าเดียวจัดการกลุ่มนี้ไม่ได้")
    print("  (ดูปัญหาข้อ 3 — เป็นข้อจำกัดเชิงโครงสร้าง ไม่ใช่เรื่องคะแนน)")
    print()

    rule("สาเหตุ")
    print("  retriever.retrieve() คืน top_k ที่ใกล้ที่สุดเสมอ ตัดออกเฉพาะ idx == -1")
    print("  ซึ่งเกิดเมื่อดัชนีมีเวกเตอร์น้อยกว่า top_k เท่านั้น (retriever.py:31-33)")
    print()
    print("  main.py:64-66 มีกิ่งที่พิมพ์ 'No relevant answer found in the knowledge base'")
    print("  เมื่อ results ว่าง แต่ results ไม่มีวันว่างตราบใดที่ดัชนีมีเวกเตอร์มากกว่า 1")
    print("  ข้อความนี้จึงไม่มีทางถูกพิมพ์ออกมา")
    print()

    rule("วิธีตรวจสอบ")
    print("  ถามเรื่องที่คลังไม่มีแน่ ๆ สัก 3-4 ข้อ แล้วดูคะแนนอันดับ 1")
    print("  ถ้ามันอยู่ในช่วงเดียวกับคำถามจริง แปลว่าใช้คะแนนตั้งเกณฑ์ไม่ได้")
    print("  ถ้าต่ำกว่าชัดเจน แปลว่าตั้งเกณฑ์ได้ และควรตั้ง")
    print()

    rule("แนวทางแก้")
    print("  ใส่เกณฑ์ตัดก่อนแสดงผล เทียบคะแนนอันดับ 1 กับค่าที่วัดมาจากคำถามสองกลุ่ม")
    print("  ต่ำกว่าเกณฑ์ให้บอกว่าคลังไม่มีเรื่องนี้ แทนที่จะแสดงเมนูที่ไม่เกี่ยว")
    print()
    print("  LAB04 ทำแบบนี้ที่ serve.py:35 ด้วยเกณฑ์ 0.50 ซึ่งวัดมาจากคำถามจริง 60 ข้อ")
    print("  เทียบกับคำถามนอกคลัง 20 ข้อ ได้ผลปฏิเสธคำถามจริงผิด 0/60")
    print()
    print("  ตัวอย่าง 4 ข้อในสคริปต์นี้น้อยเกินกว่าจะตั้งเกณฑ์จริง ๆ ได้")
    print("  ต้องเขียนคำถามนอกคลังอีกสัก 20 ข้อก่อน ซึ่งยังไม่ได้ทำ")


if __name__ == "__main__":
    run()
