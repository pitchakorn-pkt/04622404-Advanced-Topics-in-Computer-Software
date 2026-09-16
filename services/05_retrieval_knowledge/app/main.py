"""05 Retrieval / Knowledge Base

STUB: /search ตอบ chunk ปลอมหนึ่งชิ้นที่มี Source ครบทุก field
ของจริงคือ hybrid BM25 + vector รวมด้วย RRF (ดู docs/team/05_retrieval_knowledge.md)

ข้อควรระวังที่เขียนไว้ให้แล้วในเอกสาร และมีผลกับไฟล์นี้โดยตรง
  * ห้ามโหลดโมเดล embedding แบบ blocking ใน startup event
    ไม่งั้น /health จะไม่ตอบระหว่างโหลด แล้ว compose จะมองว่า container พังและวนรีสตาร์ท
    ให้โหลดครั้งแรกที่ถูกเรียกใช้ หรือโหลดใน background task
"""
from fastapi import FastAPI

from .common import health_payload, jlog, request_id_middleware  # noqa: F401
from .schemas import Chunk, SearchRequest, SearchResponse, Source

app = FastAPI(title="chuayduay · retrieval")
app.middleware("http")(request_id_middleware)


@app.get("/health")
async def health():
    return health_payload()


@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    # STUB: replace -- ของจริงค้นจากดัชนีใน INDEX_DIR
    # chunks ว่าง = "ไม่เจอ" ไม่ใช่ error ห้ามโยน 404
    jlog(event="search", top_k=req.top_k, query_len=len(req.query))
    return SearchResponse(
        request_id=req.request_id,
        chunks=[
            Chunk(
                chunk_id="it-wifi-001#p1#c1",
                text="(ตัวอย่างจาก stub) ถ้าต่อ Wi-Fi ไม่ได้ ให้ลองลืมเครือข่ายแล้วเชื่อมใหม่ก่อน",
                score=0.82, bm25_score=11.2, vector_score=0.77,
                source=Source(ref=1, doc_id="it-wifi-001",
                              title="ต่อ Wi-Fi ไม่ได้ — ไล่ตรวจทีละขั้น",
                              url="https://example.invalid/wifi", page=1,
                              date="2026-05-01", category="it_support"),
            )
        ],
        latency_ms=1,
    )
