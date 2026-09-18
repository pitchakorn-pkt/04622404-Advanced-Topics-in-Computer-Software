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

# RRF constant — 60 คือค่ามาตรฐานจากงานวิจัยต้นฉบับ (ออกแบบไว้สำหรับ web-scale ที่มีผู้สมัครนับพัน)
# แต่คลังเรามีแค่หลักร้อย chunk ค่า k ใหญ่ขนาดนั้นทำให้คะแนนของอันดับต้น ๆ ต่างกันน้อยเกินไป (1/(60+1)
# กับ 1/(60+5) ใกล้กันมาก) วัดจริงบน golden set แล้ว k=5 ให้ hit@5 ดีกว่า k=60 ชัดเจน (0.88 เทียบ 0.77
# บนคลัง 120 chunk) — นี่คือการปรับค่าคงที่ร่วมของ RRF เอง ไม่ใช่การถ่วงน้ำหนักระหว่าง BM25/vector
# แยกกัน (ซึ่งเป็นสิ่งที่ RRF ถูกเลือกมาเพื่อเลี่ยงตั้งแต่แรก) จึงยังคงหลักการเดิมของสเปกไว้
RRF_K = int(os.getenv("RRF_K", "5"))

# cross-encoder reranker (ของ "Could" ในสเปก) — วัดจริงแล้วดีขึ้นมาก (hit@5 0.80 -> 0.95) แต่โมเดลนี้
# (BAAI/bge-reranker-v2-m3, ~568M พารามิเตอร์) มีสองข้อจำกัดที่วัดได้จริงบน CPU ล้วน (ไม่มี GPU):
#   1. แรม: โหลดคู่กับ e5-base แล้ววัดได้ ~4.3GB RSS ชนเพดาน `memory: 4G` ของ service นี้พอดี
#   2. เวลา: rerank 20 candidate (RERANK_CANDIDATE_POOL) ใช้เวลา ~15 วินาทีต่อ request (วัดจาก
#      steady-state หลัง warmup) ซึ่งชนงบเวลา router->retrieval 15s ของ CONTRACT พอดีเป๊ะ แทบไม่มี
#      margin เหลือเลย ลอง bfloat16 เพื่อลดแรมแล้วกลับช้าลงไปอีก (~34s) เพราะ CPU นี้ไม่มี bf16 compute
#      path ที่เร็ว จึงไม่ใช่ทางแก้
# สรุป: ปิดไว้เป็นค่าเริ่มต้น ยังไม่ production-ready บน CPU เดี่ยว ต้องแก้อย่างน้อยหนึ่งใน
#   (ก) ขอเพิ่มเพดานแรมเป็น ~6G ใน docker-compose.yml (ของหัวหน้า) และ/หรือ
#   (ข) เปลี่ยนไปใช้ cross-encoder ที่เล็ก/เร็วกว่านี้ (แลกกับคุณภาพที่อาจตกลง ยังไม่ได้ทดลอง) และ/หรือ
#   (ค) ลด RERANK_CANDIDATE_POOL ลง (ยังไม่ได้วัดว่าคุณภาพจะตกแค่ไหน)
# เปิดทดสอบเองได้ด้วย RERANK_ENABLED=true บนเครื่องที่แรม/เวลาเหลือเยอะ (เช่น demo แบบไม่ผ่าน router จริง)
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "false").lower() == "true"
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_CANDIDATE_POOL = int(os.getenv("RERANK_CANDIDATE_POOL", "20"))

# เกณฑ์ "เจอจริง" ของผลอันดับ 1 — คะแนน RRF สะท้อนแค่อันดับ ไม่สะท้อนความมั่นใจ (คำถามมั่ว ๆ ก็ยังได้
# vector similarity สูงลิบเพราะโมเดล e5 ให้คะแนนคู่ประโยคไทยกระจุกอยู่ในช่วงแคบและสูง) จึงเช็กจากคะแนนดิบ
# ของแต่ละวิธีแทน: ต้องมี "คำซ้ำจริง" (BM25 > 0) หรือ "ความหมายใกล้พอ" (vector similarity สูงพอ) อย่างใดอย่างหนึ่ง
SEARCH_MIN_BM25_SCORE = float(os.getenv("SEARCH_MIN_BM25_SCORE", "1.0"))
SEARCH_MIN_VECTOR_SIMILARITY = float(os.getenv("SEARCH_MIN_VECTOR_SIMILARITY", "0.82"))

BM25_INDEX_PATH = os.path.join(INDEX_DIR, "bm25.pkl")
CHROMA_DIR = os.path.join(INDEX_DIR, "chroma")
CHROMA_COLLECTION = "chunks"
INDEX_META_PATH = os.path.join(INDEX_DIR, "index_meta.json")
