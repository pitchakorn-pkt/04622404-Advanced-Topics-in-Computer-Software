"""03 AI Router / Agent — สมองของระบบ

รับคำถามจาก 02 api แล้วตัดสินใจเป็นชั้น (ดู app/cascade.py) จากนั้นเรียก 04/05/06
ตามเส้นที่เลือก (ดู app/plans.py) แล้วรวมผลกลับไปพร้อมเหตุผลที่อธิบายได้

สองอย่างที่โมดูลนี้ถือไว้คนเดียวทั้งทีม
  1. **งบเวลารวม 70 วินาที** (CONTRACT ข้อ 0) — api รอเราไว้ 75s ใช้เกินเมื่อไหร่
     ผู้ใช้เห็น 504 ทั้งที่คำตอบกำลังจะเสร็จ timeout ต่อ hop อย่างเดียวกันไม่ได้
  2. **`reasoning` และ `trace`** — สิ่งที่ทำให้ระบบนี้เป็น agent ไม่ใช่กล่องดำ
     ข้อมูลไหลผ่านเราอยู่แล้ว ต้นทุนเพิ่มคือศูนย์ แต่เก็บย้อนหลังไม่ได้ถ้าไม่ใส่ตั้งแต่แรก
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import FastAPI

from . import cascade, llm, plans, rules
from .budget import Budget, Steps
from .common import forward_headers, health_payload, jlog, request_id_middleware  # noqa: F401
from .config import HISTORY_MAX_CHARS, HISTORY_MAX_MESSAGES
from .schemas import RouteRequest, RouteResponse, TokenUsage, Trace

app = FastAPI(title="chuayduay · router")
app.middleware("http")(request_id_middleware)

_client: httpx.AsyncClient | None = None


@app.on_event("startup")
async def _startup():
    # client ตัวเดียวทั้งแอป ไม่สร้างใหม่ทุก request (จะเปิด connection ทิ้งจนหมด)
    global _client
    _client = httpx.AsyncClient()
    # เช็กว่าโมเดลที่ตั้งไว้ใน GROQ_MODEL ยังอยู่จริง แต่ห้ามบล็อก startup
    # ไม่งั้น /health จะไม่ตอบ แล้ว compose จะมองว่า container พังและวนรีสตาร์ท
    asyncio.create_task(llm.check_model_alive())
    # อุ่นเครื่องตัดคำของ pythainlp ไว้ก่อน (โหลดพจนานุกรมครั้งแรกใช้เวลา ~0.4s)
    # ไม่งั้นผู้ใช้คนแรกหลัง deploy จะรอนานกว่าคนอื่นโดยไม่มีเหตุผล
    asyncio.create_task(asyncio.to_thread(rules.prepare, "อุ่นเครื่องตัดคำไวไฟ"))


@app.on_event("shutdown")
async def _shutdown():
    if _client:
        await _client.aclose()


@app.get("/health")
async def health():
    return health_payload()


def _trim_history(history: list) -> list[dict]:
    """ตัด history ไม่ให้ยาวเกิน — เอาข้อความ "ล่าสุด" ไว้ เพราะ follow-up พึ่งข้อความท้ายสุด"""
    recent = [{"role": m.role, "content": m.content} for m in history][-HISTORY_MAX_MESSAGES:]
    total = 0
    kept: list[dict] = []
    for msg in reversed(recent):
        total += len(msg["content"])
        if total > HISTORY_MAX_CHARS and kept:
            break
        kept.append(msg)
    kept.reverse()
    return kept


@app.post("/route", response_model=RouteResponse)
async def route(req: RouteRequest):
    assert _client is not None
    budget = Budget()
    steps = Steps()
    history = _trim_history(req.history)

    # file_text เป็น "ข้อมูล" ไม่ใช่ "คำสั่ง" — ห้ามเอาไปมีผลกับการเลือก route (prompt injection)
    decision = await cascade.decide(req.query, history, _client, budget, steps, req.request_id)

    outcome = await plans.execute(decision, req.query, history, req.file_text,
                                  req.request_id, _client, budget, steps)

    reasoning = decision.reasoning
    if outcome.route != decision.route:
        reasoning += f" · เปลี่ยนไปใช้เส้น {outcome.route} แทน"
    if outcome.notes:
        reasoning += " · " + " · ".join(outcome.notes)

    latency_ms = budget.elapsed_ms()
    token_usage = TokenUsage(input=decision.token_usage[0] + outcome.token_usage[0],
                             output=decision.token_usage[1] + outcome.token_usage[1])

    # decided_at_layer คือตัวเลขที่เอาไปสรุปได้ว่ากี่ % ตัดสินใจได้โดยไม่ต้องเรียก LLM
    jlog(event="route", route=outcome.route, decided_at_layer=decision.layer,
         decided_route=decision.route, category=decision.category,
         confidence=round(decision.confidence, 3), engines_used=outcome.engines_used,
         latency_ms=latency_ms, budget_left_s=round(budget.remaining(), 1),
         steps=steps.items, notes=outcome.notes)

    if budget.remaining() < 0:
        jlog(event="budget_exceeded", latency_ms=latency_ms)

    return RouteResponse(request_id=req.request_id, answer=outcome.answer,
                         sources=outcome.sources, route=outcome.route,
                         engines_used=outcome.engines_used, confidence=decision.confidence,
                         reasoning=reasoning, latency_ms=latency_ms, token_usage=token_usage,
                         trace=Trace(decided_at_layer=decision.layer, steps=steps.items))
