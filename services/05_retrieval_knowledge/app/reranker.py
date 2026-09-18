"""Cross-encoder reranker — งาน "Could" จากสเปก: ปรับอันดับ top-N ที่ hybrid คืนมาให้แม่นขึ้น

ทำงานแยกจากขั้น retrieval เดิมโดยสิ้นเชิง (ไม่ขึ้นกับว่า corpus มีกี่ chunk หรือมี howto แล้วหรือยัง)
รับผลลัพธ์ hybrid มา rerank ใหม่เท่านั้น จึงไม่ต้องรอข้อมูล howto จาก 04/07 ก่อนเริ่มทำ

ใช้ BAAI/bge-reranker-v2-m3 เพราะรองรับภาษาไทยดี (โมเดลตระกูลเดียวกับ bge-m3 ที่สเปกแนะนำไว้เป็นทางเลือก
ของ embedding — ดู docs/team/05_retrieval_knowledge.md) ไม่ต้องเพิ่ม dependency ใหม่ ใช้ sentence-transformers
ตัวเดียวกับที่มีอยู่แล้ว

ห้ามโหลดโมเดลตอน import (blocking) — โหลดครั้งแรกที่ถูกเรียกใช้จริงเท่านั้น เหมือน embeddings.py
"""
from __future__ import annotations

import math
import threading

from . import config
from .index_store import ChunkRecord

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import CrossEncoder
                _model = CrossEncoder(config.RERANKER_MODEL)
    return _model


def is_loaded() -> bool:
    return _model is not None


def rerank(query: str, candidates: list[tuple[ChunkRecord, float, float | None, float | None]], top_k: int):
    """candidates: (record, fused_score, bm25_score, vector_score) ที่มาจาก RRF ก่อน rerank
    คืนค่าเรียงใหม่ตามคะแนน cross-encoder (แทนที่ fused_score เดิมด้วยคะแนน rerank เพื่อให้ `score`
    ใน response สะท้อนอันดับสุดท้ายจริง ๆ) ตัด bm25_score/vector_score เดิมไว้เป็นข้อมูลอ้างอิงเหมือนเดิม
    """
    if not candidates:
        return []
    model = _get_model()
    pairs = [(query, rec.text) for rec, _, _, _ in candidates]
    raw_scores = model.predict(pairs)

    def sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    scored = [
        (rec, sigmoid(float(raw)), bm25_score, vector_score)
        for (rec, _fused, bm25_score, vector_score), raw in zip(candidates, raw_scores)
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]
