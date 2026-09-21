"""05 Retrieval / Knowledge Base

Hybrid BM25 (pythainlp) + vector (e5 ผ่าน Chroma) รวมด้วย RRF ตาม docs/team/05_retrieval_knowledge.md

ข้อควรระวังที่เขียนไว้ให้แล้วในเอกสาร และมีผลกับไฟล์นี้โดยตรง
  * ห้ามโหลดโมเดล embedding แบบ blocking ใน startup event
    ไม่งั้น /health จะไม่ตอบระหว่างโหลด แล้ว compose จะมองว่า container พังและวนรีสตาร์ท
    ให้โหลดครั้งแรกที่ถูกเรียกใช้ หรือโหลดใน background task (ทำทั้งสองอย่างที่นี่: อุ่นเครื่องใน
    background thread ตอน startup แบบไม่บล็อก แล้วยังคง lazy-load เผื่อ background ยังไม่เสร็จ)
"""
from __future__ import annotations

import threading
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .common import error_body, health_payload, jlog, request_id_middleware
from .retrieval import (
    Filters,
    IndexModelMismatchError,
    IndexNotReadyError,
    search_above_threshold,
    warm_up,
)
from .schemas import Chunk, SearchRequest, SearchResponse, Source

app = FastAPI(title="chuayduay · retrieval")
app.middleware("http")(request_id_middleware)


@app.on_event("startup")
async def warmup_in_background():
    def _warm():
        try:
            warm_up()  # โหลด index/model ล่วงหน้า รันใน thread แยกไม่บล็อก event loop
            jlog(event="warmup", status="ok")
        except Exception as exc:  # ไม่มีดัชนีตอน startup ก็ปล่อยผ่าน ค่อย lazy-load ตอนมี request จริง
            jlog(event="warmup", status="skipped", reason=str(exc))

    threading.Thread(target=_warm, daemon=True).start()


@app.get("/health")
async def health():
    return health_payload()


@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    started = time.perf_counter()
    filters = None
    if req.filters:
        filters = Filters(category=req.filters.category, year_from=req.filters.year_from)

    jlog(event="search", top_k=req.top_k, query_len=len(req.query))

    try:
        hits = search_above_threshold(req.query, top_k=req.top_k, filters=filters)
    except (IndexNotReadyError, IndexModelMismatchError) as exc:
        jlog(event="search_error", error=str(exc))
        return JSONResponse(status_code=503, content=error_body("RETRIEVAL_INDEX_UNAVAILABLE", str(exc)))

    chunks = [
        Chunk(
            chunk_id=hit.record.chunk_id,
            text=hit.record.text,
            score=hit.fused_score,
            bm25_score=hit.bm25_score,
            vector_score=hit.vector_score,
            source=Source(
                ref=i + 1,
                doc_id=hit.record.doc_id,
                title=hit.record.title,
                url=hit.record.url,
                page=hit.record.page,
                date=hit.record.date,
                category=hit.record.category,
            ),
        )
        for i, hit in enumerate(hits)
    ]
    return SearchResponse(
        request_id=req.request_id,
        chunks=chunks,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
