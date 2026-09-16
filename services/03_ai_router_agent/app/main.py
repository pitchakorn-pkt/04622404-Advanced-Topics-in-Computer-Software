"""03 AI Router / Agent — สมองของระบบ

STUB: ตัดสินใจด้วย keyword หยาบ ๆ แค่พอให้ทั้งเส้นวิ่งได้ครบ 5 route
**แต่เรียก 04 / 05 / 06 ผ่าน HTTP จริง** เพื่อให้รู้ตั้งแต่วันแรกว่าสายต่อกันติดหรือไม่

ของจริงคือ cascade 4 ชั้นและตาราง rule base ที่ล็อกไว้แล้ว
ดู docs/team/03_ai_router_agent.md และ docs/CONTRACT.md ข้อ 3
"""
from __future__ import annotations

import os
import time

import httpx
from fastapi import FastAPI

from .common import forward_headers, health_payload, jlog, request_id_middleware  # noqa: F401
from .schemas import RouteRequest, RouteResponse, Trace

ENGINES = os.getenv("ENGINES_URL", "http://engines:8000")
RETRIEVAL = os.getenv("RETRIEVAL_URL", "http://retrieval:8000")
GENERATION = os.getenv("GENERATION_URL", "http://generation:8000")

# งบเวลาต่อ hop ตาม CONTRACT ข้อ 0 — งบ "รวม" ทั้ง request ต้องไม่เกิน 70 วินาที
T_ENGINE, T_RETRIEVAL, T_GENERATION = 30.0, 15.0, 30.0

app = FastAPI(title="chuayduay · router")
app.middleware("http")(request_id_middleware)

_client: httpx.AsyncClient | None = None


@app.on_event("startup")
async def _startup():
    # client ตัวเดียวทั้งแอป ไม่สร้างใหม่ทุก request (จะเปิด connection ทิ้งจนหมด)
    global _client
    _client = httpx.AsyncClient()


@app.on_event("shutdown")
async def _shutdown():
    if _client:
        await _client.aclose()


@app.get("/health")
async def health():
    return health_payload()


# STUB: replace -- ของจริงใช้ตาราง rule base เต็มใน docs/team/03_ai_router_agent.md
RAG_WORDS = ("ไวไฟ", "wifi", "เน็ต", "รหัสผ่าน", "บัญชี", "แบต", "เครื่องช้า",
             "พื้นที่เต็ม", "สำรองข้อมูล", "อัปเดต", "กล้อง", "ไมค์", "สแกม")
LOCAL_WORDS = ("จำแนก", "จัดประเภท", "หมวดหมู่", "classify")
# คำอ้างอิงกลับที่ไม่มีบริบทของตัวเอง — ชั้น guard ต้องถามกลับ ไม่ใช่เดาแล้วตอบมั่ว
# ของจริงจะต่างออกไป: ถ้ามี history ให้ rewrite คำถามก่อน ไม่ใช่ถามกลับทันที
VAGUE_WORDS = ("อันนั้น", "อันนี้", "แล้วล่ะ", "ยังไงต่อ", "แบบนั้น")
DECLINE_WORDS = ("แฮก", "hack", "เจาะระบบ", "ปลอมบัตร")


def _decide(q: str) -> tuple[str, float, str, str]:
    """คืน (route, confidence, reasoning, layer)"""
    text = q.strip()
    if len(text) < 3:
        return "clarify", 0.9, "ข้อความสั้นเกินกว่าจะตีความได้", "guard"
    if any(w in text for w in DECLINE_WORDS):
        return "decline", 0.9, "เข้าข่ายคำขอที่ไม่ควรตอบ", "guard"
    if text in VAGUE_WORDS or (len(text) <= 12 and any(text.startswith(w) for w in VAGUE_WORDS)):
        return "clarify", 0.9, "ข้อความอ้างอิงกลับโดยไม่มีบริบท", "guard"
    if any(w in text for w in LOCAL_WORDS):
        return "local_ai", 0.9, "ผู้ใช้ขอให้จำแนกประเภทโดยตรง", "rules"
    hit = [w for w in RAG_WORDS if w in text]
    if hit:
        return "university_rag", 0.9, f"เจอคำในคลังความรู้: {', '.join(hit[:3])}", "rules"
    return "general_ai", 0.6, "ไม่เข้ากฎข้อไหน ตกมาที่ความรู้ทั่วไป", "rules"


@app.post("/route", response_model=RouteResponse)
async def route(req: RouteRequest):
    t0 = time.perf_counter()
    steps: list[dict] = []
    assert _client is not None
    h = forward_headers()

    def mark(name: str, started: float):
        steps.append({"name": name, "ms": int((time.perf_counter() - started) * 1000)})

    s = time.perf_counter()
    route_name, conf, reasoning, layer = _decide(req.query)
    mark(f"router.{layer}", s)
    engines_used: list[str] = []
    answer, sources = "", []

    if route_name == "clarify":
        answer = "ช่วยขยายความอีกนิดได้ไหมครับ ว่าติดปัญหาอะไรกับอุปกรณ์ตัวไหน"

    elif route_name == "decline":
        answer = "ขอโทษครับ เรื่องนี้ผมช่วยไม่ได้ ถ้าเป็นปัญหาบัญชีของตัวเองแนะนำให้ติดต่อผู้ดูแลระบบโดยตรง"

    elif route_name == "university_rag":
        s = time.perf_counter()
        r = await _client.post(f"{RETRIEVAL}/search", headers=h, timeout=T_RETRIEVAL,
                               json={"request_id": req.request_id, "query": req.query, "top_k": 5})
        chunks = r.json().get("chunks", [])
        mark("retrieval.search", s)
        engines_used.append("retrieval")
        if not chunks:
            answer = "ไม่พบข้อมูลนี้ในคลังความรู้ แนะนำให้ติดต่อเจ้าหน้าที่โดยตรงครับ"
        else:
            contexts = [{"ref": i + 1, "text": c["text"], "source": {**c["source"], "ref": i + 1}}
                        for i, c in enumerate(chunks)]
            s = time.perf_counter()
            g = await _client.post(f"{GENERATION}/generate", headers=h, timeout=T_GENERATION,
                                   json={"request_id": req.request_id, "mode": "grounded",
                                         "query": req.query, "contexts": contexts})
            mark("generation.grounded", s)
            engines_used.append("generation")
            answer, sources = g.json()["answer"], g.json()["sources"]

    else:
        endpoint, mode = (("/local/classify", "explain_local") if route_name == "local_ai"
                          else ("/general", "passthrough"))
        payload = ({"request_id": req.request_id, "text": req.query} if route_name == "local_ai"
                   else {"request_id": req.request_id, "query": req.query, "task": "qa"})
        s = time.perf_counter()
        e = await _client.post(f"{ENGINES}{endpoint}", headers=h, timeout=T_ENGINE, json=payload)
        mark(f"engines{endpoint}", s)
        engines_used.append("engines")
        s = time.perf_counter()
        g = await _client.post(f"{GENERATION}/generate", headers=h, timeout=T_GENERATION,
                               json={"request_id": req.request_id, "mode": mode,
                                     "query": req.query, "draft": e.json()["content"]})
        mark(f"generation.{mode}", s)
        engines_used.append("generation")
        answer = g.json()["answer"]

    total = int((time.perf_counter() - t0) * 1000)
    jlog(event="route", route=route_name, decided_at_layer=layer, latency_ms=total)
    return RouteResponse(request_id=req.request_id, answer=answer, sources=sources,
                         route=route_name, engines_used=engines_used, confidence=conf,
                         reasoning=reasoning, latency_ms=total,
                         trace=Trace(decided_at_layer=layer, steps=steps))
