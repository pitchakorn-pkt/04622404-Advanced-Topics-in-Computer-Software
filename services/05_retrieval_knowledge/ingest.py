"""สร้างดัชนีค้นหาจากเอกสารใน data/raw — รันด้วย `make ingest`

STUB: ยังไม่ทำอะไร เจ้าของโมดูลมาเขียนต่อ
ลำดับที่ต้องทำ: extract -> clean -> รวมคู่ถาม-ตอบเป็นเอกสาร -> chunk -> embed -> เขียนลง INDEX_DIR

อย่าลืมสามข้อจาก docs/team/05_retrieval_knowledge.md
  1. คู่ถาม-ตอบเดี่ยว ๆ สั้นเกินกว่าที่ขั้น chunk จะทำงาน ต้องรวมเป็นเอกสารก่อน
  2. หมวดภาษาไทยทั้ง 10 หมวด map เป็น category `it_support` แล้วเก็บหมวดเดิมเป็น metadata
  3. map relevant_chunk_ids ของ golden set ให้ตรงกับ chunk_id ใหม่ **ทำก่อนอย่างอื่น**
"""
import os

INDEX_DIR = os.getenv("INDEX_DIR", "/data/index")

if __name__ == "__main__":
    os.makedirs(INDEX_DIR, exist_ok=True)
    print(f"[stub] ยังไม่ได้สร้างดัชนี — โฟลเดอร์ปลายทางพร้อมแล้วที่ {INDEX_DIR}")
