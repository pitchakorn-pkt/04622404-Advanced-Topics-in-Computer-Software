"""ตัวช่วยประมวลผลภาษาไทยที่ต้องใช้ร่วมกันทั้ง train.py และ app/main.py

สำคัญ: thai_tokenizer ต้องอยู่ในโมดูลที่ import ได้เหมือนกันทั้งตอนเทรนโมเดล
(train.py) และตอนโหลดโมเดลมาใช้งานจริง (app/main.py ผ่าน joblib.load)
เพราะ TfidfVectorizer เก็บ "พาธไปยังฟังก์ชัน" ไว้ตรงๆ ตอน joblib.dump
ไม่ได้เก็บโค้ดจริง — ถ้าฟังก์ชันเดิมอยู่ใน __main__ (เช่นนิยามในไฟล์ที่รันตรงๆ
แบบ `python train.py`) โมดูลอื่นที่มา joblib.load ทีหลัง (เช่น uvicorn/pytest
ที่รันคนละ process) จะหาฟังก์ชันนี้ใน __main__ ของตัวเองไม่เจอ แล้ว unpickle
ล้มเหลวเป็น error ทั่วไป (ไม่ใช่ FileNotFoundError) จึงต้องแยกมาไว้ที่นี่
"""
from pythainlp.tokenize import word_tokenize


def thai_tokenizer(text: str) -> list[str]:
    """ตัดคำภาษาไทยด้วย pythainlp ให้ TfidfVectorizer ใช้"""
    return word_tokenize(text, engine="newmm")
