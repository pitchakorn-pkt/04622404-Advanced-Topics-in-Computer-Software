# data_loader.py
# Shared loader for every problem script in this folder.
#
# Each script reads the artefacts this system already committed — the chunk
# store, the FAISS vectors, the BM25 index and the evaluation results — instead
# of rebuilding them. Nothing here downloads a model or calls an API, so every
# problem can be reproduced from a fresh clone with no key and no GPU.

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)        # ให้ import config และ src ของ LAB04 ได้

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")


def _read_json(*parts):
    path = os.path.join(BASE_DIR, *parts)
    if not os.path.exists(path):
        raise SystemExit(f"ไม่พบไฟล์ {path}\nสร้างก่อนด้วย: cd .. && python build_index.py")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_chunks():
    """chunk ทุกชิ้นที่ระบบใช้ค้นจริง — ลำดับตรงกับแถวใน FAISS index"""
    return _read_json("vector_db", "chunk_store.json")


def load_records():
    """คู่ถาม-ตอบดิบก่อนเข้าขั้นแบ่ง chunk"""
    return _read_json("outputs", "extracted_text.json")


def load_eval_retrieval():
    return _read_json("outputs", "eval_retrieval.json")


def load_eval_generation():
    return _read_json("outputs", "eval_generation.json")


def load_eval_query_transform():
    return _read_json("outputs", "eval_query_transform.json")


def load_index_meta():
    return _read_json("vector_db", "index_meta.json")


def load_embeddings():
    """เวกเตอร์ของทุก chunk (194 x 1024) — normalize มาแล้ว จึงใช้ dot เป็น cosine ได้"""
    import numpy as np
    path = os.path.join(BASE_DIR, "outputs", "embeddings.npy")
    if not os.path.exists(path):
        raise SystemExit(f"ไม่พบ {path}\nสร้างก่อนด้วย: cd .. && python build_index.py")
    return np.load(path)


def load_bm25():
    """BM25 index ที่ build ไว้แล้ว — ค้นได้ทันทีโดยไม่ต้องโหลดโมเดล embedding"""
    import pickle
    path = os.path.join(BASE_DIR, "vector_db", "bm25_index.pkl")
    if not os.path.exists(path):
        raise SystemExit(f"ไม่พบ {path}\nสร้างก่อนด้วย: cd .. && python build_index.py")
    with open(path, "rb") as f:
        return pickle.load(f)


def source_lines():
    """บรรทัดดิบของไฟล์คลัง ใช้ตรวจคุณภาพข้อมูลต้นทาง"""
    import config
    with open(config.SOURCE_FILE, "r", encoding="utf-8") as f:
        return f.readlines()


def head(text, n=70):
    """ตัดข้อความให้สั้นพอใส่บรรทัดเดียว"""
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def rule(title=""):
    print("-" * 72)
    if title:
        print(title)
        print("-" * 72)
