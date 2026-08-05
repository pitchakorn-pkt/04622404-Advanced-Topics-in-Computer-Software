




# Central configuration for the entire project.
# Change settings here to experiment without modifying the source code.

import os
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

# 1. ลองปิดทีละตัวแล้วรัน evaluation ดูว่าคะแนนเปลี่ยนไปแค่ไหน

USE_HYBRID = True            # ค้นด้วย BM25 ควบคู่กับ dense (ปิด = dense อย่างเดียว)
USE_RERANK = True            # จัดอันดับใหม่ด้วย cross-encoder — วัดแล้ว MRR 0.7511 -> 0.8008
                             # แลกกับ 20 ms -> 528 ms ต่อคำถาม และโมเดลเพิ่มอีก 2.2 GB
                             # ปิดได้ถ้าอยากให้เบา ระบบข้ามขั้นนี้เองถ้าโหลดโมเดลไม่สำเร็จ
USE_QUERY_TRANSFORM = False      # แปลงคำถามก่อนค้น — เสีย LLM เพิ่ม 1 ครั้งต่อคำถาม
USE_MEMORY = True              # จำบทสนทนา เพื่อตอบคำถามต่อเนื่องได้
USE_LLM = True              # False = แสดงข้อความที่ค้นได้ดิบ ๆ ไม่เรียก LLM เลย
SHOW_SOURCES =  False        # True = แสดงรายการแหล่งอ้างอิงท้ายคำตอบ
SHOW_DEBUG = False          # True = แสดงคะแนนและเวลาของแต่ละขั้น


# 2. ที่อยู่ไฟล์
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_db")


# clack python build_index.py
SOURCE_FILE = os.path.join(DATA_DIR, "iot_qa.txt")
GOLDEN_SET_FILE = os.path.join(DATA_DIR, "golden_set.json")
PARAPHRASE_FILE = os.path.join(DATA_DIR, "eval_paraphrases.txt")   # คำถามเขียนใหม่ด้วยมือ ใช้วัดผลเท่านั้น

# ผลลัพธ์ระหว่างทางจาก build_index.py
EXTRACTED_TEXT_FILE = os.path.join(OUTPUT_DIR, "extracted_text.json")
CHUNKS_FILE = os.path.join(OUTPUT_DIR, "chunks.json")
EMBEDDINGS_FILE = os.path.join(OUTPUT_DIR, "embeddings.npy")
RETRIEVAL_RESULTS_FILE = os.path.join(OUTPUT_DIR, "retrieval_results.json")
EVAL_RETRIEVAL_FILE = os.path.join(OUTPUT_DIR, "eval_retrieval.json")
EVAL_GENERATION_FILE = os.path.join(OUTPUT_DIR, "eval_generation.json")

# ฐานข้อมูลที่ระบบใช้ค้นจริง
FAISS_INDEX_FILE = os.path.join(VECTOR_DB_DIR, "document.index")
CHUNK_STORE_FILE = os.path.join(VECTOR_DB_DIR, "chunk_store.json")
BM25_INDEX_FILE = os.path.join(VECTOR_DB_DIR, "bm25_index.pkl")
INDEX_META_FILE = os.path.join(VECTOR_DB_DIR, "index_meta.json")

# 3. การเตรียมข้อมูล  (แก้แล้วต้องรัน build_index.py ใหม่)
CHUNK_SIZE = 400        # ตัวอักษรต่อ chunk (คำตอบส่วนใหญ่สั้นกว่านี้อยู่แล้ว)
CHUNK_OVERLAP = 50      # ให้ chunk ที่ติดกันเหลื่อมกัน กันใจความขาดตอน

# ตัวโมเดลจริงถูกดาวน์โหลดไปเก็บที่ ~/.cache/huggingface (ย้ายได้ด้วยตัวแปร HF_HOME)
#
# เลือก bge-m3 จากการวัดจริงบน golden set ชุดเดียวกัน (variant paraphrase, dense อย่างเดียว)
#
#   paraphrase-multilingual-MiniLM-L12-v2   384 มิติ · 128 token   MRR 0.3799 · 5.9 ms/คำถาม
#   intfloat/multilingual-e5-base           768 มิติ · 512 token   MRR 0.6075 · 8.5 ms/คำถาม
#   BAAI/bge-m3                            1024 มิติ · 8192 token  MRR 0.7388 · 22.3 ms/คำถาม
#
# bge-m3 เข้ารหัสคลังช้ากว่า MiniLM 17 เท่า (224s เทียบกับ 13s) แต่เป็นงานครั้งเดียว
# ส่วนเวลาต่อคำถามต่างกันแค่ 16 มิลลิวินาที ซึ่งน้อยมากเทียบกับเวลาที่ LLM ใช้เขียนคำตอบ
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"

# 4. การค้นหา
TOP_K = 3               # ส่งกี่ chunk ให้ LLM เขียนคำตอบ
CANDIDATE_K = 20        # ดึง TOP_K
RRF_K = 60              # ค่าคงที่ของสูตร RRF

# น้ำหนักของแต่ละวิธีตอนรวมอันดับ — ค่าเท่ากันคือสูตร RRF ดั้งเดิม
# ปรับได้เมื่อวัดแล้วพบว่าวิธีหนึ่งแม่นกว่าอีกวิธีอย่างสม่ำเสมอในคลังนี้
DENSE_WEIGHT = 1.0
BM25_WEIGHT = 1.0

RERANK_MODEL_NAME = "BAAI/bge-reranker-v2-m3"   # ใช้เมื่อ USE_RERANK = True

QUERY_TRANSFORM_MODE = "multi_query"   # rewrite | multi_query | hyde
MULTI_QUERY_COUNT = 3

# 5. LLM
LLM_PROVIDER = "groq"
LLM_MODEL = ""          # เว้นว่าง = ใช้ค่า default
LLM_TEMPERATURE = 0.2   # เหมือนค่าเทรดโฮล
LLM_MAX_TOKENS = 800

# (base_url, โมเดลเริ่มต้น, ชื่อตัวแปรสภาพแวดล้อมที่เก็บ key)
# ทุกเจ้าเรียกผ่านไลบรารี openai ตัวเดียวกัน เพราะมี endpoint ที่เข้ากันได้
# key อ่านจากตัวแปรสภาพแวดล้อมเสมอ ห้ามเขียนลงไฟล์นี้แล้ว commit ขึ้น git
LLM_PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "GROQ_API_KEY"),
    "ollama": ("http://localhost:11434/v1", "llama3.1:8b", None),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini", "OPENAI_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/",
               "gemini-1.5-flash", "GOOGLE_API_KEY"),
}


# 6. ข้อความและการวัดผล
MEMORY_MAX_TURNS = 6    # จำนวนรอบของการจำบทสนทนา
NO_CONTEXT_MESSAGE = "ขออภัย ไม่พบข้อมูลที่เกี่ยวข้อง"
DISCLAIMER = "หมายเหตุ: ข้อมูลนี้ใช้เพื่อการศึกษา ควรตรวจสอบกับเอกสารของผู้ผลิตก่อนใช้งานจริง"

EVAL_K_VALUES = [1, 3, 5, 10]
GOLDEN_SET_SIZE = 60


# create output directories if they don't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(VECTOR_DB_DIR, exist_ok=True)
