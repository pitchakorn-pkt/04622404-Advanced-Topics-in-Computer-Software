"""ค่าคอนฟิกของ service นี้ อ่านจาก env ตามชื่อใน docs/CONTRACT.md ข้อ 7
ตัวแปรที่ไม่ได้อยู่ใน CONTRACT (CHUNK_*, SEARCH_*) เป็นค่าปรับจูนภายในของ retrieval เท่านั้น
"""
from __future__ import annotations

import os

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
INDEX_DIR = os.getenv("INDEX_DIR", "/data/index")
HF_HOME = os.getenv("HF_HOME")

DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
RAW_DIR = os.path.join(DATA_DIR, "raw")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.csv")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# RRF constant (ค่ามาตรฐานที่ใช้กันทั่วไป ไม่ต้อง tune)
RRF_K = int(os.getenv("RRF_K", "60"))

# เกณฑ์ "เจอจริง" ของผลอันดับ 1 — คะแนน RRF สะท้อนแค่อันดับ ไม่สะท้อนความมั่นใจ (คำถามมั่ว ๆ ก็ยังได้
# vector similarity สูงลิบเพราะโมเดล e5 ให้คะแนนคู่ประโยคไทยกระจุกอยู่ในช่วงแคบและสูง) จึงเช็กจากคะแนนดิบ
# ของแต่ละวิธีแทน: ต้องมี "คำซ้ำจริง" (BM25 > 0) หรือ "ความหมายใกล้พอ" (vector similarity สูงพอ) อย่างใดอย่างหนึ่ง
SEARCH_MIN_BM25_SCORE = float(os.getenv("SEARCH_MIN_BM25_SCORE", "1.0"))
SEARCH_MIN_VECTOR_SIMILARITY = float(os.getenv("SEARCH_MIN_VECTOR_SIMILARITY", "0.82"))

BM25_INDEX_PATH = os.path.join(INDEX_DIR, "bm25.pkl")
CHROMA_DIR = os.path.join(INDEX_DIR, "chroma")
CHROMA_COLLECTION = "chunks"
INDEX_META_PATH = os.path.join(INDEX_DIR, "index_meta.json")
