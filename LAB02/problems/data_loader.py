# data_loader.py
# Shared loader for the problem scripts in this folder.
#
# Everything that can be answered from the committed artefacts — the chunk
# store, the FAISS vectors, the parsed records — is read straight from disk.
# Only the problems that need to encode a *new* query load the embedding model,
# and they share one instance through get_retriever().

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)        # ให้ import config และ src ของ LAB02 ได้

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")

_retriever = None


def _read_json(*parts):
    path = os.path.join(BASE_DIR, *parts)
    if not os.path.exists(path):
        raise SystemExit(f"ไม่พบไฟล์ {path}\nสร้างก่อนด้วย: cd .. && python labs/lab01_extract_text.py ... lab04")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_chunks():
    """chunk ทุกชิ้นที่ระบบใช้ค้นจริง — ลำดับตรงกับแถวใน FAISS index"""
    return _read_json("vector_db", "chunk_store.json")


def load_records():
    """คู่ถาม-ตอบดิบก่อนเข้าขั้นแบ่ง chunk"""
    return _read_json("outputs", "extracted_text.json")


def load_embeddings():
    """เวกเตอร์ของทุก chunk (90 x 384) — normalize มาแล้ว จึงใช้ dot เป็น cosine ได้"""
    import numpy as np
    return np.load(os.path.join(BASE_DIR, "outputs", "embeddings.npy"))


def sample_questions():
    """คำถามทดสอบ 10 ข้อ — ไม่มีสคริปต์ไหนในโปรเจกต์อ่านไฟล์นี้"""
    path = os.path.join(BASE_DIR, "data", "sample_questions.txt")
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def get_retriever():
    """
    Retriever ตัวเดียวกับที่ main.py ใช้ โหลดครั้งเดียวแล้วใช้ซ้ำ

    ตัวนี้ต้องโหลดโมเดล embedding จึงช้ากว่าส่วนอื่นราวสองสามวินาที
    """
    global _retriever
    if _retriever is None:
        import config
        from src.retriever import Retriever
        _retriever = Retriever(
            model_name=config.EMBEDDING_MODEL_NAME,
            index_path=config.FAISS_INDEX_FILE,
            chunk_store_path=config.CHUNK_STORE_FILE,
        )
    return _retriever


def head(text, n=70):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def rule(title=""):
    print("-" * 72)
    if title:
        print(title)
        print("-" * 72)
