"""07 Response / Log / Feedback — ความจำของระบบ

STUB: เก็บทุกอย่างไว้ในหน่วยความจำของ process ยังไม่ได้ต่อ postgres
ของจริงดู docs/team/07_response_logging.md

สี่กติกาที่พลาดแล้วพังเงียบ ใส่ไว้ใน stub นี้แล้วเพื่อกันลืมตอนเขียนของจริง
  1. limit = จำนวนข้อความ "ล่าสุด" -> ORDER BY created_at DESC LIMIT n แล้วค่อยกลับลำดับ
  2. feedback.message_id ห้ามเป็น FOREIGN KEY เพราะโหวตมาถึงก่อน log ได้
  3. session ที่ยังไม่มีข้อมูล ตอบ 200 พร้อม messages: [] ห้ามตอบ 404
  4. /log ต้อง idempotent ด้วย request_id เพราะ 02 retry สองครั้ง
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Response

from .common import health_payload, jlog, request_id_middleware  # noqa: F401
from .schemas import FeedbackIn, LogEntry

app = FastAPI(title="chuayduay · response-log")
app.middleware("http")(request_id_middleware)

# STUB: replace -- ของจริงเป็นตาราง conversations / messages / feedback ใน postgres
_seen_requests: set[str] = set()
_conversations: dict[str, dict] = {}
_messages: list[dict] = []
_feedback: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@app.get("/health")
async def health():
    return health_payload()


@app.post("/log", status_code=202)
async def write_log(entry: LogEntry):
    # กติกาข้อ 4 — ยิงซ้ำ request_id เดิมต้องไม่เกิดแถวซ้ำ
    if entry.request_id in _seen_requests:
        jlog(event="log_duplicate", session_id=entry.session_id)
        return {"accepted": True}
    _seen_requests.add(entry.request_id)

    # 07 สร้างแถว conversation ให้เอง 02 ไม่ได้เรียก endpoint สร้าง session แยก
    conv = _conversations.setdefault(entry.session_id, {
        "session_id": entry.session_id, "user_id": entry.user_id,
        "title": entry.user_message[:40], "created_at": _now()})
    conv["updated_at"] = _now()

    for mid, role, content, src in (
        (entry.user_message_id, "user", entry.user_message, []),
        (entry.assistant_message_id, "assistant", entry.answer, entry.sources),
    ):
        _messages.append({"message_id": mid, "session_id": entry.session_id, "role": role,
                          "content": content, "sources": src, "route": entry.route,
                          "created_at": _now()})
    jlog(event="log", session_id=entry.session_id, route=entry.route)
    return {"accepted": True}


@app.post("/feedback")
async def feedback(body: FeedbackIn):
    # กติกาข้อ 2 — รับได้แม้ยังไม่มีแถว message นั้น แล้วค่อยเชื่อมกันตอนอ่าน
    _feedback[body.message_id] = {"rating": body.rating, "user_id": body.user_id,
                                  "comment": body.comment, "created_at": _now()}
    jlog(event="feedback", rating=body.rating)
    return {"ok": True}


@app.get("/sessions")
async def sessions(user_id: str):
    items = [{"session_id": c["session_id"], "title": c["title"],
              "updated_at": c.get("updated_at", c["created_at"])}
             for c in _conversations.values() if c["user_id"] == user_id]
    items.sort(key=lambda c: c["updated_at"], reverse=True)
    return {"sessions": items}


@app.get("/history/{session_id}")
async def history(session_id: str, user_id: str, limit: int = 20):
    conv = _conversations.get(session_id)
    # กติกาข้อ 3 — ยังไม่มีข้อมูลให้ตอบ 200 พร้อม list ว่าง ห้าม 404
    if conv is None:
        return {"session_id": session_id, "messages": []}
    # เช็กความเป็นเจ้าของเป็นหน้าที่ของเรา ไม่ใช่ของ 02 (ตาราง conversations เป็นของเรา)
    if conv["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="ไม่พบบทสนทนานี้")
    rows = [m for m in _messages if m["session_id"] == session_id]
    # กติกาข้อ 1 — เอา n รายการ "ล่าสุด" แล้วกลับลำดับให้เป็นเก่า->ใหม่
    rows = rows[-limit:]
    for m in rows:
        m["rating"] = (_feedback.get(m["message_id"]) or {}).get("rating")
    return {"session_id": session_id, "messages": rows}


@app.get("/stats")
async def stats(days: int = 7):
    # STUB: replace -- คำนวณตอนอ่าน ไม่ใช่ตอน log
    by_route: dict[str, int] = {}
    for m in _messages:
        if m["role"] == "assistant" and m.get("route"):
            by_route[m["route"]] = by_route.get(m["route"], 0) + 1
    up = sum(1 for f in _feedback.values() if f["rating"] == 1)
    down = sum(1 for f in _feedback.values() if f["rating"] == -1)
    return {"total_requests": len(_seen_requests), "avg_latency_ms": 0, "p95_latency_ms": 0,
            "by_route": by_route, "feedback": {"up": up, "down": down},
            "error_rate": 0.0, "top_downvoted": []}
