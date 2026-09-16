# -*- coding: utf-8 -*-
# Problem 02: the words the user types are not the words the corpus stores
#
# Runs the real BM25 index from vector_db/bm25_index.pkl. No embedding model is
# loaded, so this reproduces the keyword half of retrieval exactly as the system
# does it, in about a second.
#
# Three separate failures live under this one heading:
#   1. cross-script  — the user types "otp", the corpus says "โอทีพี"
#   2. tokenisation  — newmm shreds Thai transliterations it does not know
#   3. paraphrase    — BM25 collapses as soon as the wording changes

from data_loader import head, load_bm25, load_chunks, load_eval_retrieval, rule

from pythainlp.tokenize import word_tokenize
from src.query_transform import normalize_query
from src.thai_text import CUSTOM_DICT, DOMAIN_WORDS, tokenize

# คู่ที่ความหมายเดียวกัน ต่างกันแค่ผู้ใช้พิมพ์อังกฤษ ส่วนคลังเขียนเป็นคำทับศัพท์ไทย
CROSS_SCRIPT = ["otp ไม่มา", "cloud เต็ม", "ทำ backup", "bluetooth ไม่ติด"]

# คำไทยที่คนสะกดผิดกันประจำ — คลังเขียนอีกแบบ
MISSPELLED = ["อัพเดทแล้วช้า"]


def bm25_top1(bm25, chunks, query):
    """ค้นด้วย BM25 ตัวจริง คืน (คะแนน, คำถามของ chunk อันดับ 1)"""
    scores = bm25.get_scores(tokenize(query))
    best = max(range(len(scores)), key=lambda i: scores[i])
    return float(scores[best]), chunks[best]["question"]


def show_pair(bm25, chunks, typed):
    fixed = normalize_query(typed)
    before_score, before_q = bm25_top1(bm25, chunks, typed)
    after_score, after_q = bm25_top1(bm25, chunks, fixed)
    changed = "  <-- ได้เอกสารคนละชิ้น" if before_q != after_q else ""

    print(f'  ผู้ใช้พิมพ์     "{typed}"')
    print(f"     โทเคน       {tokenize(typed)}")
    print(f"     BM25 อันดับ 1 {before_score:6.2f}  {head(before_q, 42)}")
    print(f'  หลัง normalize "{fixed}"')
    print(f"     BM25 อันดับ 1 {after_score:6.2f}  {head(after_q, 42)}{changed}")
    print()


def run():
    chunks = load_chunks()
    bm25 = load_bm25()

    rule("1. คำเดียวกันคนละระบบตัวอักษร — BM25 มองเป็นคนละคำ")
    for query in CROSS_SCRIPT:
        show_pair(bm25, chunks, query)

    print("  สะกดผิดก็ให้ผลแบบเดียวกัน — เอกสารชิ้นเดิม แต่คะแนนต่างเกือบเท่าตัว")
    print()
    for query in MISSPELLED:
        show_pair(bm25, chunks, query)

    print("  SLANG_MAP (query_transform.py:48-69) คือตัวอุดช่องนี้ ทำงานก่อนถึงขั้นค้น")
    print("  ไม่ใช้ AI ไม่มีต้นทุน จึงเปิดไว้ตลอดผ่าน normalize_query()")
    print()

    rule("2. ตัวตัดคำไทยไม่รู้จักคำทับศัพท์")
    changed = []
    for word in DOMAIN_WORDS:
        plain = word_tokenize(word, engine="newmm")
        withdict = word_tokenize(word, engine="newmm", custom_dict=CUSTOM_DICT)
        if plain != withdict:
            changed.append((word, plain, withdict))

    print(f"  {len(changed)} จาก {len(DOMAIN_WORDS)} คำใน DOMAIN_WORDS ถูกตัดผิดถ้าใช้พจนานุกรมมาตรฐาน")
    print()
    for word, plain, withdict in changed:
        print(f"  {word:<16} {str(plain):<38} -> {withdict}")
    print()
    print("  เศษที่ได้ไม่ใช่คำ จึงไม่มีวันตรงกับโทเคนฝั่งคลัง การค้นด้วยคำพวกนี้จึงพลาด")
    print("  ทั้งที่เอกสารมีอยู่จริง")
    print()
    print("  กับดัก: dict_trie() ของ pythainlp *แทนที่* พจนานุกรมหลัก ไม่ใช่รวมเข้าไป")
    print("  ถ้าส่งเฉพาะคำของเราไป คำไทยอื่นจะไม่ถูกรู้จักเลย ต้องส่ง")
    print("  set(thai_words()) | set(DOMAIN_WORDS) เสมอ (thai_text.py:49)")
    print()
    print("  ข้อควรรู้: คำอธิบายหัวไฟล์ thai_text.py:17-21 ยังยกตัวอย่างเป็น")
    print('  "ออสซิลโลสโคป" กับ "ไมโครคอนโทรลเลอร์" ซึ่งเป็นคำจากคลัง IoT ชุดก่อน')
    print("  ทั้งสองคำไม่ได้อยู่ใน DOMAIN_WORDS ปัจจุบันแล้ว ตัวเลข 15/43 ในคอมเมนต์นั้น")
    print(f"  จึงเป็นของคลังเก่า ของคลังปัจจุบันคือ {len(changed)}/{len(DOMAIN_WORDS)} ตามที่พิมพ์ข้างบน")
    print()

    rule("3. BM25 พังเมื่อเปลี่ยนสำนวน — คำถามเดียวกันเขียนคนละแบบ")
    variants = load_eval_retrieval()["results"]["bm25_only"]["by_variant"]
    print(f"  {'variant':<14}{'MRR':>10}{'hit@1':>10}")
    for name in ["verbatim", "slang", "partial", "natural", "paraphrase"]:
        v = variants[name]
        print(f"  {name:<14}{v['mrr']:>10.4f}{v['hit@1']:>10.4f}")
    print()
    print("  verbatim (คำถามลอกมาจากคลังตรง ๆ) ได้เต็ม 1.0000")
    print("  paraphrase (เขียนใหม่ด้วยมือ เหลือคำซ้ำเฉลี่ย 25%) เหลือ 0.4953")
    print("  ตัวเลขคู่นี้บอกว่า BM25 จับ 'คำที่ตรงกัน' ไม่ใช่ 'ความหมาย'")
    print("  dense บน paraphrase ชุดเดียวกันได้ 0.8961 — ต่างกันเกือบสองเท่า")
    print()

    rule("ไม่ตัด stopword ภาษาไทย — ทดลองแล้วแย่ลง ไม่ใช่ดีขึ้น")
    print("  ตัด stopword   MRR 0.4970   (โทเคนเฉลี่ย 50 ตัวต่อเอกสาร)")
    print("  ไม่ตัด         MRR 0.6136   (โทเคนเฉลี่ย 90 ตัวต่อเอกสาร)")
    print()
    print("  BM25 ลดน้ำหนักคำที่พบทุกที่ด้วย IDF อยู่แล้ว การตัดทิ้งจึงไม่ได้อะไรเพิ่ม")
    print("  แต่ทำให้ความยาวเอกสารสั้นลงเกือบครึ่ง ซึ่งไปกวนสูตรถ่วงความยาวของ BM25")
    print('  ทั้งคลัง และรายการ 1030 คำของ pythainlp ตัด "ทำไม" "ยังไง" "ต่างกัน" ทิ้งด้วย')
    print("  ซึ่งเป็นคำที่บอกว่าผู้ใช้กำลังถามอะไร (เหตุผลเต็มอยู่ใน thai_text.py:51-59)")


if __name__ == "__main__":
    run()
