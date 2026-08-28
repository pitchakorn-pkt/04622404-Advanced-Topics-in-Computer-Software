# -*- coding: utf-8 -*-
# Problem 03: the chunking stage never runs, and its setting contradicts the model
#
# Two findings, both measured on the committed index:
#   1. 90 records go in and 90 chunks come out. Nothing has ever been split.
#   2. CHUNK_SIZE is 400 characters, but the embedding model reads at most 128
#      tokens — about 356 characters of this Thai text, measured live with the
#      model's own tokeniser. A chunk of the size the configuration allows would
#      be silently truncated before it was embedded.

from data_loader import head, load_chunks, load_records, rule

import config
from src.text_splitter import split_text

def token_lengths(chunks):
    """นับโทเคนของทุก chunk ด้วย tokenizer ของโมเดลตัวจริง (ต้องโหลดโมเดล)"""
    from data_loader import get_retriever
    model = get_retriever().embedding_model.model
    tokenizer = model.tokenizer
    return model.max_seq_length, [len(tokenizer.encode(c["text"])) for c in chunks]


def run():
    records = load_records()
    chunks = load_chunks()
    lengths = [len(c["text"]) for c in chunks]
    split = [c for c in chunks if c.get("part_idx", 0) > 0]

    rule("1. ขั้นแบ่ง chunk ไม่เคยทำงาน")
    print(f"  CHUNK_SIZE      {config.CHUNK_SIZE} ตัวอักษร")
    print(f"  CHUNK_OVERLAP   {config.CHUNK_OVERLAP} ตัวอักษร")
    print()
    print(f"  record เข้า      {len(records)}")
    print(f"  chunk ออก       {len(chunks)}")
    print(f"  chunk ที่ถูกแบ่ง  {len(split)}   <-- ศูนย์")
    print()
    print(f"  ความยาว chunk: สั้นสุด {min(lengths)}  ยาวสุด {max(lengths)}  เฉลี่ย {sum(lengths)/len(lengths):.1f}")
    print(f"  ห่างจากเกณฑ์ {config.CHUNK_SIZE} อยู่ {config.CHUNK_SIZE - max(lengths)} ตัวอักษร")
    print()
    print("  split_text() คืนข้อความทั้งก้อนเมื่อสั้นกว่าเกณฑ์ (text_splitter.py)")
    print("  และ 1 คู่ถาม-ตอบในคลังนี้ยาวไม่ถึง 400 สักคู่เดียว")
    print("  CHUNK_OVERLAP = 50 จึงไม่มีผลอะไรกับระบบนี้เลย")
    print()

    rule("2. เกณฑ์ที่ตั้งไว้ใหญ่กว่าที่โมเดลอ่านได้")
    print("  (ขั้นนี้ต้องโหลดโมเดล ใช้เวลาสักครู่)")
    max_tokens, counts = token_lengths(chunks)
    over = [n for n in counts if n > max_tokens]
    longest = max(range(len(counts)), key=lambda i: counts[i])
    chars_per_token = len(chunks[longest]["text"]) / counts[longest]
    limit_chars = max_tokens * chars_per_token

    print()
    print(f"  โมเดล            {config.EMBEDDING_MODEL_NAME}")
    print(f"  อ่านได้สูงสุด      {max_tokens} โทเคน")
    print()
    print(f"  วัดจาก chunk ทั้ง {len(chunks)} ชิ้นด้วย tokenizer ของโมเดลเอง:")
    print(f"    โทเคน สั้นสุด {min(counts)}  ยาวสุด {max(counts)}  เฉลี่ย {sum(counts)/len(counts):.1f}")
    print(f"    เกิน {max_tokens} โทเคน: {len(over)} จาก {len(chunks)} ชิ้น")
    print()
    print(f"  chunk ที่ยาวที่สุดคือ {len(chunks[longest]['text'])} ตัวอักษร = {counts[longest]} โทเคน")
    print(f"  อัตราส่วนของข้อความไทยชุดนี้จึงราว {chars_per_token:.2f} ตัวอักษรต่อโทเคน")
    print(f"  เพดาน {max_tokens} โทเคนเท่ากับราว {limit_chars:.0f} ตัวอักษร")
    print(f"  แต่ CHUNK_SIZE ตั้งไว้ {config.CHUNK_SIZE} — สูงกว่าที่โมเดลอ่านได้ {config.CHUNK_SIZE - limit_chars:.0f} ตัวอักษร")
    print()
    print("  ตอนนี้ยังไม่มีปัญหาเพราะไม่มี chunk ไหนยาวถึงเกณฑ์ แต่ถ้าวันหนึ่งมี")
    print("  chunk ที่ยาวเต็ม 400 ตัวอักษร ส่วนท้ายจะถูกตัดทิ้งก่อนเข้าโมเดล")
    print("  โดยไม่มีคำเตือน — sentence-transformers ตัดให้เงียบ ๆ ไม่ throw error")
    print()
    print("  ผลคือ chunk นั้นจะถูกค้นเจอด้วยเนื้อหาครึ่งแรกเท่านั้น ส่วนครึ่งหลัง")
    print("  ไม่มีอยู่ในดัชนีเลย ทั้งที่ยังแสดงให้ผู้ใช้เห็นเต็ม ๆ ตอนตอบ")
    print()

    rule("ถ้าขั้นแบ่งเริ่มทำงาน มันจะแบ่งแบบไหน")
    long_text = chunks[0]["text"] * 2
    pieces = split_text(long_text, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    print(f"  ทดลองกับข้อความยาว {len(long_text)} ตัวอักษร ได้ {len(pieces)} ชิ้น")
    for i, piece in enumerate(pieces):
        print(f"    ชิ้นที่ {i} ({len(piece)} ตัวอักษร) ลงท้าย: ...{piece[-40:]}")
    print()
    print("  แบ่งด้วยการนับตัวอักษรล้วน ไม่ดูขอบเขตคำหรือประโยค")
    print("  ภาษาไทยไม่มีช่องว่างคั่นคำ การตัดจึงลงกลางคำเกือบทุกครั้ง")
    print()

    rule("วิธีตรวจสอบ")
    print("  รันสคริปต์นี้หลังแก้คลังทุกครั้ง แล้วดูสามบรรทัด")
    print("    - chunk ที่ถูกแบ่ง      ยังเป็น 0 แปลว่าขั้นนี้ยังไม่ทำงาน")
    print("    - ความยาวสูงสุด        เข้าใกล้ CHUNK_SIZE แปลว่ากำลังจะเริ่ม")
    print(f"    - จำนวนโทเคนสูงสุด     เข้าใกล้ {max_tokens} แปลว่ากำลังจะโดนตัด")
    print()

    rule("แนวทางแก้")
    print(f"  ตั้ง CHUNK_SIZE ให้ต่ำกว่าเพดานของโมเดลจริง — ราว {limit_chars*0.85:.0f} ตัวอักษร")
    print("  สำหรับโมเดลตัวนี้กับข้อความไทย ค่าปัจจุบันสัญญาสิ่งที่โมเดลทำไม่ได้")
    print()
    print("  หรือเปลี่ยนไปใช้โมเดลที่รับได้ยาวกว่า LAB04 ใช้ BAAI/bge-m3 ซึ่งรับ 8192")
    print("  โทเคน ทำให้ข้อจำกัดนี้หายไปทั้งหมด")
    print()
    print("  ยังไม่ได้แก้ เพราะดัชนีและตัวเลขที่รายงานไว้ใน README วัดบนค่าชุดปัจจุบัน")


if __name__ == "__main__":
    run()
