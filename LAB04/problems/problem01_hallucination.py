# -*- coding: utf-8 -*-
# Problem 01: the system answers a question the corpus has nothing to say about
#
# The prompt already forbids it (prompt_templates.py:16, rule 2), and the
# generator already returns NO_CONTEXT_MESSAGE when retrieval comes back empty
# (generator.py:84-89). Neither is enough: dense retrieval never comes back
# empty. FAISS returns the top_k nearest vectors for any query, so `chunks` is
# always non-empty and rule 2 is left to the model's discretion.
#
# Measured on the 20 generation questions: the refusal rate is 0.00.

from data_loader import head, load_eval_generation, rule

RELEVANCE_MIN = 0.50        # serve.py:35 — เกณฑ์ที่เพิ่มเข้ามาทีหลังเพื่อปิดช่องนี้

# วัดไว้ตอนตั้งเกณฑ์ (serve.py:26-33) คำถามจริง 60 ข้อ vs คำถามนอกคลัง 20 ข้อ
REAL_QUESTION_MIN = 0.5071
REAL_QUESTION_MEDIAN = 0.6469
OUT_OF_SCOPE_CAUGHT = 13
OUT_OF_SCOPE_TOTAL = 20

# คำถามในโดเมนแต่กว้างเกินไป ที่เกณฑ์จับไม่ได้ (dense cosine ที่วัดได้จริง)
TOO_BROAD = [
    ("โทรศัพท์พังทำยังไงดี", 0.6457),
    ("คอมมีปัญหา", 0.6231),
]


def run():
    data = load_eval_generation()
    summary = data["summary"]
    results = data["results"]

    rule("อาการ — ระบบไม่เคยตอบว่าไม่รู้เลย")
    print(f"คำถามที่วัด            : {summary['จำนวนข้อ']} ข้อ")
    print(f"อัตราการตอบว่าไม่รู้    : {summary['อัตราการตอบว่าไม่รู้']:.2f}   <-- ไม่เคยปฏิเสธสักครั้ง")
    print(f"อัตราค้นเจอ chunk ที่ถูก : {summary['อัตราค้นเจอ chunk ที่ถูก']:.2f}")
    print(f"correctness            : {summary['correctness']:.4f}")
    print()
    print("ค้นเจอ chunk ที่ถูก 95% แต่ correctness ได้แค่ 0.60 — ส่วนต่างคือคำตอบที่")
    print("เขียนออกมาทั้งที่ข้อมูลไม่พอ ซึ่งกฎข้อ 2 ใน SYSTEM_PROMPT สั่งให้ปฏิเสธ")
    print()

    # ข้อที่ค้นไม่เจอ chunk ที่ถูกเลย แต่ยังตอบ = หลักฐานตรงตัวที่สุด
    unsupported = [r for r in results if not r["context_hit"] and not r["refused"]]
    rule(f"ข้อที่ค้นไม่เจอ chunk ที่ถูก แต่ยังตอบอยู่ดี ({len(unsupported)} ข้อ)")
    for item in unsupported:
        print(f"  คำถาม     : {head(item['query'])}")
        print(f"  ตอบว่า    : {head(item['answer'], 62)}")
        print(f"  refused={item['refused']}  faithfulness={item['faithfulness']:.4f}")
        print()

    rule("สาเหตุ")
    print("dense retrieval ไม่มีวันคืนค่าว่าง — FAISS คืนเพื่อนบ้านที่ใกล้ที่สุดเสมอ")
    print("ไม่ว่าคำถามจะเกี่ยวกับคลังหรือไม่ ด่านที่ generator.py:84 ดักไว้จึงไม่เคยทำงาน")
    print("เหลือแค่กฎในภาษาธรรมชาติที่ฝากความหวังไว้กับ LLM ว่าจะยอมปฏิเสธเอง")
    print()

    rule("วิธีตรวจสอบ")
    print("ถามเรื่องที่คลังไม่มีแน่ ๆ แล้วดูว่ามีคำตอบออกมาไหม ถ้ามี = ช่องนี้เปิดอยู่")
    print("ตัววัดที่ใช้คือ อัตราการตอบว่าไม่รู้ ใน outputs/eval_generation.json")
    print("ต้องดูคู่กับ อัตราค้นเจอ chunk ที่ถูก เสมอ ดูตัวเดียวแยกกันจะไม่เห็นปัญหา")
    print()

    rule("แนวทางแก้ที่ทำไปแล้ว — เกณฑ์ตัดก่อนถึง LLM (serve.py:35)")
    print(f"ใช้ cosine ของ dense hit อันดับ 1 เทียบกับเกณฑ์ {RELEVANCE_MIN:.2f}")
    print(f"  คำถามจริง 60 ข้อ : ต่ำสุด {REAL_QUESTION_MIN}  มัธยฐาน {REAL_QUESTION_MEDIAN}")
    print(f"  ที่เกณฑ์ {RELEVANCE_MIN:.2f}     : ปฏิเสธคำถามจริงผิด 0/60")
    print(f"                    จับคำถามนอกคลังได้ {OUT_OF_SCOPE_CAUGHT}/{OUT_OF_SCOPE_TOTAL}")
    print()
    print("ต้องใช้คะแนน dense ไม่ใช่คะแนน rerank — cross-encoder ให้คะแนนเชิงจัดอันดับ")
    print('ไม่ได้สอบเทียบ มันให้ "ช่วยหน่อย" 0.8161 และ "hello" 0.7271 (ดูปัญหาข้อ 6)')
    print()

    rule("ที่ยังเหลืออยู่ — คำถามกว้างเกินในโดเมนเดียวกัน")
    for question, score in TOO_BROAD:
        print(f"  {question:<24} dense = {score:.4f}  ผ่านเกณฑ์ทั้งที่ตอบให้ตรงไม่ได้")
    print()
    print("เคสแบบนี้ควรถามกลับเพื่อให้ผู้ใช้ระบุอาการ ไม่ใช่ปฏิเสธ และยังไม่ได้ทำ")


if __name__ == "__main__":
    run()
