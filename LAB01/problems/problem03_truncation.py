# -*- coding: utf-8 -*-
# Problem 03: the chunk budget is counted in one tokenizer and spent in another
#
# The Chunking stage sizes chunks with tiktoken cl100k_base and caps them at
# 500 tokens, comfortably under the 512 the embedding model accepts. By that
# count nothing is too long. Measured with the embedding model's own tokenizer,
# a third of the corpus is over the limit and gets truncated.
#
# Loads the embedding model, so this one takes a few seconds.

import statistics

from data_loader import chunks, head, rule

from chunking import DEFAULT_ENCODING
from embedding import embedding_text

MODEL_NAME = "BAAI/bge-small-en-v1.5"     # ค่าเริ่มต้นของ SentenceTransformersProvider


def run():
    corpus = chunks()
    stored = [c["token_count"] for c in corpus]

    rule("สิ่งที่ขั้น chunking เชื่อ")
    print(f"  chunk ทั้งหมด            {len(corpus)}")
    print(f"  ตัวนับที่ใช้              tiktoken {DEFAULT_ENCODING} (chunking.py:87-101)")
    print(f"  token_count ที่บันทึกไว้  ต่ำสุด {min(stored)}  สูงสุด {max(stored)}  มัธยฐาน {statistics.median(stored)}")
    print(f"  เกิน 512 ตามตัวนับนี้     {sum(1 for n in stored if n > 512)}/{len(stored)}")
    print()
    print("  ขั้น chunking ตั้งเพดานไว้ที่ 500 โทเคน ต่ำกว่า 512 ที่โมเดลรับได้")
    print("  ตามตัวเลขชุดนี้จึงไม่มี chunk ไหนยาวเกิน แม้แต่ชิ้นเดียว")
    print()

    rule("สิ่งที่โมเดลเห็นจริง")
    print("  (โหลดโมเดล ใช้เวลาสักครู่)")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    limit = model.max_seq_length
    tokenizer = model.tokenizer

    full = [len(tokenizer(embedding_text(c))["input_ids"]) for c in corpus]
    with_header = sum(1 for c in corpus if embedding_text(c) != c["text"])

    print()
    print(f"  โมเดล                    {MODEL_NAME}")
    print(f"  max_seq_length           {limit}")
    print()
    print(f"  โทเคนของ chunk           ต่ำสุด {min(full)}  สูงสุด {max(full)}  มัธยฐาน {statistics.median(full):.0f}")
    print()

    over = sum(1 for n in full if n > limit)
    dropped = sum(n - limit for n in full if n > limit)
    print(f"  chunk ที่ถูกตัด            {over}/{len(full)} = {over/len(full)*100:.1f}%")
    print(f"  โทเคนที่หายไป             {dropped:,}")
    print()
    print(f"  ตัวเลขนี้ยังต่ำกว่าความจริง — embedding_text() เติม header (ชื่อตำแหน่ง")
    print(f"  บริษัท สถานที่) เข้าไปหน้าข้อความก่อน embed แต่ header อ่านจากฟิลด์")
    print(f"  retrieval_metadata ซึ่งขั้น 04_metadata.py เป็นคนเติม และผลลัพธ์ของ")
    print(f"  ขั้นนั้น (metadata_*.json) ไม่ได้ถูก commit ไว้ในคลังนี้")
    print(f"  ตอนนี้จึงมี {with_header}/{len(corpus)} chunk ที่มี header ให้วัด")
    print(f"  ของจริงที่รันเต็มสายจะเกินเพดานมากกว่านี้")
    print()

    rule("สาเหตุ")
    print("  ตัวนับสองตัวไม่ใช่ตัวเดียวกัน")
    print(f"    ขั้น chunking  tiktoken {DEFAULT_ENCODING} — BPE ของ OpenAI")
    print("    ขั้น embedding  tokenizer ของ bge — WordPiece ของ BERT")
    print()
    print("  ข้อความชิ้นเดียวกันได้จำนวนโทเคนไม่เท่ากัน และ bge นับได้มากกว่า")
    worst = max(range(len(corpus)), key=lambda i: full[i] - corpus[i]["token_count"])
    c = corpus[worst]
    print()
    print(f"  ตัวอย่างที่ต่างกันมากที่สุด")
    print(f"    tiktoken บอก  {c['token_count']:>4} โทเคน")
    print(f"    bge เห็นจริง   {full[worst]:>4} โทเคน   ต่างกัน {full[worst] - c['token_count']}")
    print(f"    {head(c['text'], 60)}")
    print()
    print("  ขั้น chunking จึงตั้งงบไว้ในหน่วยหนึ่ง แล้วขั้น embedding ใช้จ่ายในอีกหน่วยหนึ่ง")
    print("  เพดาน 500 ที่ดูปลอดภัยจึงไม่ปลอดภัยจริง")
    print()
    print("  ส่วน header ที่ embedding_text() เติมเข้าไป (ชื่อตำแหน่ง บริษัท สถานที่)")
    print("  ก็กินโควตาอีกส่วนหนึ่ง ซึ่งไม่มีใครหักออกจากงบตอนแบ่ง chunk")
    print()

    rule("อาการเวลาเกิดขึ้นจริง")
    print("  sentence-transformers ตัดให้เงียบ ๆ โมเดลแค่หยุดอ่าน และเวกเตอร์ที่ได้")
    print("  ยังมีความกว้างถูกต้องเหมือนเดิม ไม่มี error ไม่มีอะไรผิดสังเกต")
    print()
    print("  ส่วนที่ถูกตัดคือส่วนที่จ่ายค่าประมวลผลไปแล้วในขั้น chunking และหายไปเลย")
    print("  chunk นั้นจะค้นเจอได้ด้วยเนื้อหาส่วนต้นเท่านั้น แต่ยังถูกส่งให้ LLM เต็ม ๆ")
    print("  ตอนตอบ — สิ่งที่ค้นกับสิ่งที่อ่านจึงไม่ใช่ข้อความเดียวกัน")
    print()

    rule("สิ่งที่มีอยู่แล้ว และสิ่งที่ยังขาด")
    print("  embedding.py:234-240 นับและเตือนไว้แล้วทุกครั้งที่รัน")
    print('    WARNING: n/m texts are longer than 512 tokens and will be truncated')
    print("  ซึ่งเป็นสิ่งที่ถูกต้อง — มันบอกออกมาดัง ๆ แทนที่จะปล่อยให้ไปเจอทีหลัง")
    print("  ในรูปของผลการค้นที่แย่ลงโดยไม่รู้สาเหตุ")
    print()
    print("  ที่ยังขาดคือ ไม่มีอะไร *ป้องกัน* มัน คำเตือนนี้ออกมาหลังจากที่ chunk")
    print("  ถูกสร้างและจ่ายค่าไปแล้ว และไม่มีขั้นไหนอ่านคำเตือนนี้กลับไปปรับเพดาน")
    print()

    rule("แนวทางแก้")
    print("  ให้ขั้น chunking นับด้วย tokenizer ตัวเดียวกับที่ขั้น embedding จะใช้")
    print("  แทนที่จะใช้ tiktoken เป็นตัวแทน แล้วหักความยาวของ header ออกจากงบด้วย")
    print()
    print("  ถ้าไม่อยากผูกสองขั้นเข้าด้วยกัน ให้ลดเพดานลงเผื่อส่วนต่างที่วัดได้จริง")
    print("  จากตัวเลขข้างบน ซึ่งจะได้ผลกับคลังนี้ แต่ต้องวัดใหม่เมื่อเปลี่ยนโมเดล")
    print()
    print("  บันทึกไว้ใน README ของแล็บนี้คือ MiniLM ตัด 72.7% ส่วน bge ตัด 2.6%")
    print("  ซึ่งเป็นตัวเลขตอนเลือกโมเดลเมื่อ ก.ค. 2026 ตัวเลขที่วัดได้วันนี้ไม่ตรงกับ")
    print("  ชุดนั้นแล้ว เพราะขั้น chunking เปลี่ยนไปหลังจากนั้น และไม่มีอะไรวัดซ้ำ")
    print("  ให้ — ซึ่งเป็นปัญหาเดียวกับที่ทำให้เขียนเรื่องนี้ขึ้นมา")


if __name__ == "__main__":
    run()
