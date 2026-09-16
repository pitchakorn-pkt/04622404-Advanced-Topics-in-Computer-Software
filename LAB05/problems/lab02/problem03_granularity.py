# -*- coding: utf-8 -*-
# Problem 03: one vector per Q&A pair decides which questions can ever be answered
#
# build_chunks() makes one chunk, and therefore one vector, out of each Q&A pair.
# Retrieval is nearest-neighbour search over those vectors. A question whose
# answer is spread across several pairs has no vector to be near, so no amount
# of tuning can retrieve it.
#
# Runs the real retriever over the ten questions in data/sample_questions.txt.

from _cases import AGGREGATE, SINGLE
from data_loader import get_retriever, head, load_chunks, rule


def run():
    chunks = load_chunks()
    retriever = get_retriever()
    print()

    rule("คำถามที่เจาะจงเมนูเดียว — คลังมีคู่ถาม-ตอบรองรับตรง ๆ")
    right_menu = right_entry = 0
    for query, expected in SINGLE.items():
        hits = retriever.retrieve(query, top_k=3)
        top = hits[0]
        menu_ok = top["category"] == expected
        entry_ok = menu_ok and query.replace(" ", "") in top["question"].replace(" ", "")
        right_menu += menu_ok
        right_entry += entry_ok

        print(f"  {'ถูก' if menu_ok else 'ผิด'}  {head(query, 44)}")
        print(f"      ได้ [{top['category']}] {head(top['question'], 40)}  {top['score']:.4f}")
        if menu_ok and not entry_ok:
            for rank, hit in enumerate(hits[1:], start=2):
                if query.replace(" ", "") in hit["question"].replace(" ", ""):
                    print(f"      คู่ที่ตรงคำถามอยู่อันดับ {rank}  {hit['score']:.4f}  {head(hit['question'], 34)}")
    print()
    print(f"  ได้เมนูถูก      {right_menu}/{len(SINGLE)}")
    print(f"  ได้คู่ที่ตรงคำถาม {right_entry}/{len(SINGLE)}")
    print()
    print("  ขั้นค้นหาทำงานได้ดีกับคำถามกลุ่มนี้ ที่พลาดคือพลาดภายในเมนูเดียวกัน")
    print("  ไม่ใช่ไปคนละเมนู")
    print()

    rule("คำถามที่ต้องดูหลายเมนูพร้อมกัน")
    for query in AGGREGATE:
        hits = retriever.retrieve(query, top_k=3)
        print(f"  {head(query, 44)}")
        for rank, hit in enumerate(hits, start=1):
            print(f"      {rank}. {hit['score']:.4f}  [{hit['category']}] {head(hit['question'], 36)}")
        print()

    print(f"  ทั้ง {len(AGGREGATE)} ข้อไม่มีข้อไหนได้คำตอบที่ถูก และไม่มีทางได้")
    print()

    rule("สาเหตุ")
    print(f"  คลังมี {len(chunks)} เวกเตอร์ = {len(chunks)} คู่ถาม-ตอบ หนึ่งคู่ต่อหนึ่งเวกเตอร์")
    print("  (text_splitter.build_chunks สร้าง chunk หนึ่งชิ้นต่อ record หนึ่งอัน)")
    print()
    print('  คำถามอย่าง "เมนูไหนเผ็ดที่สุด" ต้องเทียบความเผ็ดของทั้ง 15 เมนู')
    print("  คำตอบจึงกระจายอยู่ใน 15 คู่ ไม่ได้อยู่ในคู่ไหนคู่เดียว")
    print("  การค้นหาเพื่อนบ้านที่ใกล้ที่สุดไม่มีเวกเตอร์ให้ไปใกล้")
    print()
    print("  ระบบจึงคืนคู่ที่ 'พูดเรื่องความเผ็ด' มาแทน ซึ่งใกล้ที่สุดจริงตามความหมาย")
    print("  แต่ไม่ใช่คำตอบของคำถาม นี่ไม่ใช่การจัดอันดับผิด แต่เป็นคำถามที่อยู่นอก")
    print("  ความสามารถของโครงสร้างที่เลือกไว้")
    print()

    rule("วิธีตรวจสอบ")
    print("  แยกคำถามทดสอบเป็นสองกลุ่มก่อนวัดเสมอ — กลุ่มที่มีคำตอบอยู่ในหน่วยเดียว")
    print("  กับกลุ่มที่ต้องรวมหลายหน่วย แล้วรายงานแยกกัน")
    print()
    print(f"  ถ้ารวมกันจะได้ตัวเลขเดียวที่ปนกันสองเรื่อง — ที่นี่คือ {right_entry}/10")
    print("  ซึ่งอ่านเหมือนระบบค้นได้ครึ่งเดียว ทั้งที่จริงคือค้นได้เกือบหมดในกลุ่มที่")
    print("  ค้นได้ และค้นไม่ได้เลยในกลุ่มที่โครงสร้างไม่รองรับ")
    print()

    rule("แนวทางแก้")
    print("  ปัญหานี้แก้ที่การปรับจูนไม่ได้ ต้องเพิ่มความสามารถ")
    print()
    print("  1. เพิ่มคู่ถาม-ตอบระดับภาพรวมเข้าไปในคลัง เช่น 'เมนูไหนใช้กะทิบ้าง'")
    print("     ตรงไปตรงมาที่สุด และเป็นทางที่เข้ากับโครงสร้างเดิม")
    print()
    print("  2. ทำดัชนีระดับเมนูเพิ่มอีกชั้น แล้วเลือกชั้นตามชนิดของคำถาม")
    print("     ทำให้ระบบซับซ้อนขึ้นมาก เกินขอบเขตของแล็บนี้")
    print()
    print("  3. อย่างน้อยที่สุด บอกผู้ใช้ว่าระบบตอบคำถามแบบไหนได้")
    print("     ตอนนี้มันตอบทุกคำถามด้วยความมั่นใจเท่ากันหมด (ดูปัญหาข้อ 5)")


if __name__ == "__main__":
    run()
