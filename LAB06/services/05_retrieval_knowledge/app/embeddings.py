"""ห่อ sentence-transformers ไว้ที่เดียว — บังคับ prefix ของตระกูล e5 ที่นี่ที่เดียว
ลืม prefix ครั้งเดียว คุณภาพ retrieval ตกทั้งระบบแบบเงียบ ๆ (ไม่มี error ให้เห็น) จึงรวมไว้จุดเดียวไม่ให้พลาด

ห้ามโหลดโมเดลตอน import ไฟล์นี้ (blocking) — โหลดครั้งแรกที่ถูกเรียกใช้จริงเท่านั้น
ไม่งั้น /health จะค้างตอน container เพิ่งขึ้น แล้ว compose จะมองว่าไม่ healthy
"""
from __future__ import annotations

import threading

from . import config

_QUERY_PREFIX = "query: "
_PASSAGE_PREFIX = "passage: "

_model = None
_model_name = None
_lock = threading.Lock()


def _get_model():
    global _model, _model_name
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model_name = config.EMBEDDING_MODEL
                _model = SentenceTransformer(_model_name)
    return _model


def is_loaded() -> bool:
    return _model is not None


def embed_passages(texts: list[str]):
    model = _get_model()
    return model.encode([_PASSAGE_PREFIX + t for t in texts], normalize_embeddings=True, show_progress_bar=False)


def embed_query(text: str):
    model = _get_model()
    return model.encode([_QUERY_PREFIX + text], normalize_embeddings=True, show_progress_bar=False)[0]
