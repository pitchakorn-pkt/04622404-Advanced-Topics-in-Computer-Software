# -*- coding: utf-8 -*-
# Problem 09: the measurement itself is the part most likely to lie
#
# Every number quoted in the other eight problems comes from these files. This
# one asks whether they can be trusted, and shows four ways they nearly were not:
#
#   1. four of the five question variants sit at a ceiling and decide nothing
#   2. the evaluator once skipped a step the real system performs
#   3. a stage that failed on every single call reported plausible numbers
#   4. the corpus and the exam were written by the same person

from data_loader import load_eval_query_transform, load_eval_retrieval, rule

VARIANTS = ["verbatim", "slang", "partial", "natural", "paraphrase"]
CONFIGS = ["dense_only", "bm25_only", "hybrid", "hybrid+rerank"]


def ceiling():
    rule("1. เพดานของชุดข้อสอบ — 4 ใน 5 variant แยกคอนฟิกไม่ออกเลย")
    data = load_eval_retrieval()
    print(f"  MRR ของทุกคอนฟิก แยกตาม variant (คำถาม {data['n_items']} ข้อ)")
    print()
    print(f"  {'variant':<12}" + "".join(f"{c:>16}" for c in CONFIGS))
    for variant in VARIANTS:
        row = f"  {variant:<12}"
        for config_name in CONFIGS:
            row += f"{data['results'][config_name]['by_variant'][variant]['mrr']:>16.4f}"
        print(row)
    print()
    print("  สี่แถวบนได้ 1.0000 เท่ากันหมดทุกคอนฟิก รวมทั้ง bm25_only ที่อ่อนที่สุด")
    print("  ถ้าดูแต่แถวพวกนี้จะสรุปว่า 'ทุกคอนฟิกดีเท่ากัน' ซึ่งผิด")
    print()
    print("  สาเหตุ: variant พวกนี้สร้างจากคำถามในคลังโดยแก้เพียงเล็กน้อย เหลือคำซ้ำ")
    print("  กับต้นฉบับ 1.00 / 1.00 / 0.99 / 0.86 การค้นจึงเป็นการจับคู่คำตรงตัว")
    print("  ส่วน paraphrase เขียนใหม่ด้วยมือทั้ง 60 ข้อ เหลือคำซ้ำเฉลี่ย 25%")
    print()
    print("  paraphrase จึงเป็นแถวเดียวที่ตัดสินอะไรได้ และเป็นแถวที่ใช้รายงานทุกที่")
    print("  บทเรียน: ชุดข้อสอบที่ทุกคอนฟิกได้เต็ม ไม่ได้แปลว่าระบบดี แปลว่าข้อสอบวัดไม่ได้")
    print()


def skipped_step():
    rule("2. ตัววัดเคยข้ามขั้นที่ระบบจริงทำ")
    print("  main.py เรียก normalize_query() ก่อนค้นทุกครั้ง แต่ eval_retrieval เดิม")
    print("  ส่งคำถามดิบเข้าไปตรง ๆ ตัวเลขที่ได้จึงต่ำกว่าระบบจริง")
    print()
    print("  แก้แล้วที่ evaluation/eval_retrieval.py:74-76 — เติม normalize_query()")
    print("  ให้ตรงกับที่ main.py ทำ")
    print()
    print("  บั๊กอีกตัวในไฟล์เดียวกัน: รายการ all_misses ถูกเขียนทับทุกรอบ เหลือแค่")
    print("  คอนฟิกสุดท้าย ทำให้วิเคราะห์ข้อที่ค้นไม่เจอข้ามคอนฟิกไม่ได้")
    print()
    print("  ทั้งสองตัวมีอาการเหมือนกัน: ตัวเลขที่ออกมา 'ดูสมเหตุสมผล' จึงไม่มีใครสงสัย")
    print("  วิธีจับคือไล่เทียบว่าเส้นทางของตัววัดผ่านขั้นเดียวกับเส้นทางจริงครบไหม")
    print()


def silent_failure():
    rule("3. ขั้นที่ล้มเหลวทุกครั้ง แต่รายงานตัวเลขที่ดูปกติ")
    data = load_eval_query_transform()
    print(f"  ผลที่ commit ไว้ (คำถาม {data['n_items']} ข้อ):")
    print()
    print(f"  {'คอนฟิก':<22}{'MRR(para)':>11}{'llm_calls':>11}{'ล้มเหลว':>9}{'ใช้ได้':>8}")
    for name, row in data["results"].items():
        mrr = row["by_variant"]["paraphrase"]["mrr"]
        print(f"  {name:<22}{mrr:>11.4f}{row['llm_calls']:>11}{row['llm_failures']:>9}{str(row['usable']):>8}")
    print()
    print("  สังเกตว่าไม่มีแถวของโหมดที่ใช้ LLM (rewrite / multi_query / hyde) เลย")
    print("  ทั้งสามโหมดยังวัดไม่สำเร็จ จึงไม่มีตัวเลขให้รายงาน")
    print()
    print("  ที่มา: QueryTransformer.transform() ดัก exception แล้วคืนคำถามเดิมเงียบ ๆ")
    print("  (query_transform.py:147-149) ซึ่งถูกต้องสำหรับตอนใช้งานจริง — ขั้นนี้ล้ม")
    print("  ไม่ควรทำให้ทั้งระบบล่ม")
    print()
    print("  แต่ตอนวัดผลมันกลายเป็นกับดัก: โควตา Groq ฟรีหมด ทุกครั้งที่เรียก LLM ล้มเหลว")
    print("  ตัววัดจึงวัด 'คำถามเดิมที่ไม่ได้แปลง' ทั้ง 60 ข้อ แล้วรายงานเป็นคะแนนของ")
    print("  โหมดนั้น ตัวเลขออกมาสวยและสมเหตุสมผล ทั้งที่ขั้นที่กำลังวัดไม่ได้ทำงานเลย")
    print()
    print("  แก้โดยห่อ LLM ด้วย CountingLLM (evaluation/eval_query_transform.py:27)")
    print("  ที่นับ llm_calls / llm_failures แล้วตั้งธง usable = (failures == 0)")
    print("  (บรรทัด 124-126) แถวที่ usable = false ห้ามเอาไปใช้อ้างอิง")
    print()
    print("  หลักการที่ได้: ทุกขั้นที่ 'ถอยกลับอย่างนุ่มนวล' เวลาใช้งานจริง ต้อง")
    print("  'ส่งเสียงดัง' เวลาวัดผล ไม่งั้นจะได้ตัวเลขของสิ่งที่ไม่ได้ทำงาน")
    print()


def limits():
    rule("4. ข้อจำกัดที่แก้ไม่ได้ด้วยโค้ด")
    print("  คลังกับชุดข้อสอบเขียนโดยคนเดียวกัน ผู้เขียนย่อมถามด้วยกรอบความคิดเดียวกับ")
    print("  ตอนเขียนคำตอบ ตัวเลขทุกตัวจึงเป็นขอบบน ไม่ใช่ผลที่คาดหวังจากผู้ใช้จริง")
    print("  ทางแก้คือให้คนอื่นเขียนคำถามทดสอบ ซึ่งยังไม่ได้ทำ")
    print()
    print("  คำถามทดสอบมี 60 ข้อ กับคลัง 194 คู่ ความต่าง 1-2 ข้อจึงยังอยู่ในระดับ")
    print("  ที่บังเอิญได้ ต้องดูนัยสำคัญประกอบเสมอ:")
    print("    ผสม BM25 ทำให้แย่ลง   dense ชนะ 14 : hybrid 1   p = 0.0009   สรุปได้")
    print("    rerank ช่วยจริง        0 : 18                     p < 0.001    สรุปได้")
    print("    dense vs hybrid+rerank 0 : 5                      p = 0.063    อ่านเป็นแนวโน้ม")
    print()
    print("  ตัวชี้วัดที่มีประโยชน์คือ 'จำนวนข้อที่พลิก' ไม่ใช่ค่าเฉลี่ย ตอนขยายคลัง")
    print("  จาก 172 เป็น 194 คู่ ค่าเฉลี่ยแทบไม่ขยับ (ผิด 3 เป็น 4 ข้อ) แต่จำนวนข้อ")
    print("  ที่พลิกระหว่างคอนฟิกกว้างขึ้น และ p ดีขึ้นสิบเท่า")


def run():
    ceiling()
    skipped_step()
    silent_failure()
    limits()


if __name__ == "__main__":
    run()
