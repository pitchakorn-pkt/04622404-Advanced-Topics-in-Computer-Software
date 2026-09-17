"""Hybrid retrieval: BM25 (pythainlp) + vector (e5 ผ่าน Chroma) รวมด้วย RRF
บวก cross-encoder reranker เสริม (ของ "Could" ในสเปก) เป็นขั้นสุดท้ายก่อนตัด top_k

ใช้ทั้งจาก main.py (online, ผ่าน HTTP) และ eval_retrieval.py (offline, เรียกฟังก์ชันตรง ๆ
เพื่อวัด BM25-only / vector-only / hybrid / hybrid+rerank แยกกันตาม golden set)
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

from . import config, embeddings, reranker
from .index_store import ChunkRecord, load_bm25, load_chroma_collection, load_index_meta
from .text_processing import segment_thai


class IndexModelMismatchError(RuntimeError):
    pass


class IndexNotReadyError(RuntimeError):
    pass


@dataclass
class Filters:
    category: str | None = None
    year_from: int | None = None


@dataclass
class SearchHit:
    record: ChunkRecord
    fused_score: float
    bm25_score: float | None
    vector_score: float | None


_engine = None
_lock = threading.Lock()


class _Engine:
    def __init__(self):
        meta = load_index_meta()
        if meta and meta.get("embedding_model") != config.EMBEDDING_MODEL:
            raise IndexModelMismatchError(
                f"index ถูกสร้างด้วยโมเดล {meta.get('embedding_model')} "
                f"แต่ตอนนี้ตั้ง EMBEDDING_MODEL={config.EMBEDDING_MODEL} — ต้อง re-index (`make ingest`) ก่อน"
            )
        bm25_data = load_bm25()
        if bm25_data is None:
            raise IndexNotReadyError("ยังไม่มีดัชนี — รัน `make ingest` ก่อน")
        self.bm25, self.records = bm25_data
        self.record_by_id: dict[str, ChunkRecord] = {r.chunk_id: r for r in self.records}
        self.collection = load_chroma_collection()


def _get_engine() -> _Engine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = _Engine()
    return _engine


def is_ready() -> bool:
    return _engine is not None


def warm_up() -> None:
    """เรียกจาก background thread ตอน startup เพื่อโหลด index/model ล่วงหน้าแบบไม่บล็อก /health
    ต้องเรียก embed_query จริงด้วย ไม่ใช่แค่เปิดดัชนี ไม่งั้น sentence-transformers ยังโหลดตอน request แรกอยู่ดี
    """
    engine = _get_engine()
    if engine.collection is not None:
        embeddings.embed_query("อุ่นเครื่อง")
    if config.RERANK_ENABLED and engine.records:
        reranker.rerank("อุ่นเครื่อง", [(engine.records[0], 0.0, None, None)], top_k=1)


def _passes_filters(rec: ChunkRecord, filters: Filters | None) -> bool:
    if filters is None:
        return True
    if filters.category and rec.category != filters.category:
        return False
    if filters.year_from:
        year = None
        if rec.date:
            try:
                year = int(rec.date[:4])
            except ValueError:
                year = None
        if year is None or year < filters.year_from:
            return False
    return True


def bm25_rank(query: str, filters: Filters | None, limit: int) -> list[tuple[ChunkRecord, float]]:
    engine = _get_engine()
    tokens = segment_thai(query)
    scores = engine.bm25.get_scores(tokens)
    order = sorted(range(len(engine.records)), key=lambda i: scores[i], reverse=True)
    out: list[tuple[ChunkRecord, float]] = []
    for i in order:
        rec = engine.records[i]
        if not _passes_filters(rec, filters):
            continue
        out.append((rec, float(scores[i])))
        if len(out) >= limit:
            break
    return out


def vector_rank(query: str, filters: Filters | None, limit: int) -> list[tuple[ChunkRecord, float]]:
    engine = _get_engine()
    if engine.collection is None or engine.collection.count() == 0:
        return []
    query_embedding = embeddings.embed_query(query)
    n_results = min(engine.collection.count(), max(limit * 5, limit))
    res = engine.collection.query(query_embeddings=[query_embedding.tolist()], n_results=n_results)
    out: list[tuple[ChunkRecord, float]] = []
    for chunk_id, distance in zip(res["ids"][0], res["distances"][0]):
        rec = engine.record_by_id.get(chunk_id)
        if rec is None or not _passes_filters(rec, filters):
            continue
        similarity = 1.0 - distance
        out.append((rec, similarity))
        if len(out) >= limit:
            break
    return out


def _rrf_fuse(
    ranked_lists: list[list[tuple[ChunkRecord, float]]],
    limit: int,
) -> list[SearchHit]:
    rrf_scores: dict[str, float] = {}
    bm25_scores: dict[str, float] = {}
    vector_scores: dict[str, float] = {}
    record_by_id: dict[str, ChunkRecord] = {}

    bm25_list, vector_list = ranked_lists
    for rank, (rec, score) in enumerate(bm25_list, start=1):
        record_by_id[rec.chunk_id] = rec
        rrf_scores[rec.chunk_id] = rrf_scores.get(rec.chunk_id, 0.0) + 1.0 / (config.RRF_K + rank)
        bm25_scores[rec.chunk_id] = score
    for rank, (rec, score) in enumerate(vector_list, start=1):
        record_by_id[rec.chunk_id] = rec
        rrf_scores[rec.chunk_id] = rrf_scores.get(rec.chunk_id, 0.0) + 1.0 / (config.RRF_K + rank)
        vector_scores[rec.chunk_id] = score

    ranked_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:limit]
    return [
        SearchHit(
            record=record_by_id[cid],
            fused_score=rrf_scores[cid],
            bm25_score=bm25_scores.get(cid),
            vector_score=vector_scores.get(cid),
        )
        for cid in ranked_ids
    ]


def _as_hits(ranked: list[tuple[ChunkRecord, float]], top_k: int, is_bm25: bool) -> list[SearchHit]:
    out = []
    for rec, score in ranked[:top_k]:
        out.append(SearchHit(
            record=rec,
            fused_score=score,
            bm25_score=score if is_bm25 else None,
            vector_score=None if is_bm25 else score,
        ))
    return out


def search(
    query: str,
    top_k: int = 5,
    filters: Filters | None = None,
    method: str = "hybrid",
) -> list[SearchHit]:
    """method: 'hybrid' (default, ของจริงที่ /search ใช้เมื่อ RERANK_ENABLED=false) | 'bm25' | 'vector'
    | 'rerank' (hybrid ต่อด้วย cross-encoder — ของจริงที่ /search ใช้เมื่อ RERANK_ENABLED=true ค่าเริ่มต้น)
    สามอันแรกไว้ให้ eval_retrieval.py เทียบกันว่าทำไมต้อง hybrid (+rerank)
    """
    candidate_pool = max(top_k * 10, 50)

    if method == "bm25":
        return _as_hits(bm25_rank(query, filters, candidate_pool), top_k, is_bm25=True)
    if method == "vector":
        return _as_hits(vector_rank(query, filters, candidate_pool), top_k, is_bm25=False)

    rerank_pool = max(candidate_pool, config.RERANK_CANDIDATE_POOL)
    bm25_list = bm25_rank(query, filters, rerank_pool)
    vector_list = vector_rank(query, filters, rerank_pool)
    fused = _rrf_fuse([bm25_list, vector_list], limit=rerank_pool)

    if method == "hybrid":
        return fused[:top_k]
    if method == "rerank":
        candidates = [(h.record, h.fused_score, h.bm25_score, h.vector_score)
                      for h in fused[:config.RERANK_CANDIDATE_POOL]]
        reranked = reranker.rerank(query, candidates, top_k)
        return [SearchHit(record=r, fused_score=s, bm25_score=b, vector_score=v) for r, s, b, v in reranked]
    raise ValueError(f"unknown method: {method}")


def _is_confident(hit: SearchHit) -> bool:
    if hit.bm25_score is not None and hit.bm25_score >= config.SEARCH_MIN_BM25_SCORE:
        return True
    if hit.vector_score is not None and hit.vector_score >= config.SEARCH_MIN_VECTOR_SIMILARITY:
        return True
    return False


def search_above_threshold(query: str, top_k: int, filters: Filters | None) -> list[SearchHit]:
    """เช็ค 'เจอจริงไหม' จากคะแนนดิบของ hybrid เสมอ (ไม่ขึ้นกับ reranker) แล้วค่อยตัดสินใจว่าจะคืน
    ผลแบบ hybrid ตรง ๆ หรือส่งต่อให้ cross-encoder จัดอันดับใหม่ก่อนคืน top_k
    """
    hybrid_hits = search(query, top_k=top_k, filters=filters, method="hybrid")
    if not hybrid_hits or not _is_confident(hybrid_hits[0]):
        return []
    if config.RERANK_ENABLED:
        return search(query, top_k=top_k, filters=filters, method="rerank")
    return hybrid_hits
