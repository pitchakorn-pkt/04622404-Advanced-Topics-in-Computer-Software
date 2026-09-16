"""02 API / Backend — ประตูหน้าบ้าน

STUB: auth เป็นผู้ใช้ตัวอย่างในหน่วยความจำ ยังไม่ได้ต่อ postgres
**แต่เรียก router และ response-log ผ่าน HTTP จริง** ทั้งเส้นจึงวิ่งได้ตั้งแต่วันแรก

ของจริงดู docs/team/02_api_backend.md โดยเฉพาะ "ลำดับ 10 ขั้นของ /api/chat"
ที่ทำผิดลำดับแล้วพังเงียบ — ลำดับนั้นถูกใส่ไว้ในฟังก์ชัน chat() ด้านล่างแล้ว
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone

import httpx
import jwt
from fastapi import BackgroundTasks, Cookie, FastAPI, HTTPException, Response

from .common import error_body, forward_headers, health_payload, jlog, request_id_middleware  # noqa: F401
from .schemas import ChatRequest, ChatResponse, FeedbackRequest, LoginRequest

ROUTER = os.getenv("ROUTER_URL", "http://router:8000")
RLOG = os.getenv("RESPONSE_LOG_URL", "http://response-log:8000")
SECRET = os.getenv("JWT_SECRET_KEY", "dev-only-change-me")
T_ROUTER = 75.0   # ต้องมากกว่างบรวมของ router (70s) ตาม CONTRACT ข้อ 0

# STUB: replace -- ของจริงเก็บในตาราง users พร้อม bcrypt hash
DEMO_USERS = {"student": "student", "staff": "staff", "demo": "demo"}

app = FastAPI(title="chuayduay · api")
app.middleware("http")(request_id_middleware)

_client: httpx.AsyncClient | None = None


@app.on_event("startup")
async def _startup():
    global _client
    _client = httpx.AsyncClient()


@app.on_event("shutdown")
async def _shutdown():
    if _client:
        await _client.aclose()


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _user_from_cookie(token: str | None) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="ยังไม่ได้เข้าสู่ระบบ")
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="เซสชันหมดอายุ")


@app.get("/health")
async def health():
    return health_payload()


@app.post("/api/auth/login")
async def login(body: LoginRequest, response: Response):
    if DEMO_USERS.get(body.username) != body.password:
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    user = {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, body.username)),
            "username": body.username, "display_name": body.username, "role": "student"}
    token = jwt.encode(user, SECRET, algorithm="HS256")
    # httpOnly กัน JavaScript อ่าน token ได้ — ลดผลกระทบถ้าโดน XSS
    response.set_cookie("access_token", token, httponly=True, samesite="lax", path="/")
    return {"user": user}


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@app.get("/api/auth/me")
async def me(access_token: str | None = Cookie(default=None)):
    return {"user": _user_from_cookie(access_token)}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, bg: BackgroundTasks,
               access_token: str | None = Cookie(default=None)):
    t0 = time.perf_counter()
    assert _client is not None
    h = forward_headers()

    user = _user_from_cookie(access_token)                                  # 1
    session_id = body.session_id or str(uuid.uuid4())                       # 3 (07 สร้างแถวให้เอง)
    user_mid, asst_mid = str(uuid.uuid4()), str(uuid.uuid4())               # 7

    history: list[dict] = []                                                # 4
    try:
        r = await _client.get(f"{RLOG}/history/{session_id}", headers=h, timeout=10,
                              params={"user_id": user["id"], "limit": 10})
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="ไม่พบบทสนทนานี้")
        # 5 แปลง Message -> HistoryMessage เอาแค่ role กับ content
        history = [{"role": m["role"], "content": m["content"]} for m in r.json()["messages"]]
    except HTTPException:
        raise
    except Exception as exc:
        jlog(event="history_unavailable", error=str(exc))   # 07 ล่มห้ามทำให้ chat พัง

    # 6 file_text — STUB: replace เมื่อทำ /api/upload จริง
    try:                                                                    # 8
        rr = await _client.post(f"{ROUTER}/route", headers=h, timeout=T_ROUTER, json={
            "request_id": h["X-Request-ID"], "session_id": session_id,
            "user": {"id": user["id"], "role": user.get("role", "student")},
            "query": body.message, "history": history})
        rr.raise_for_status()
        data = rr.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="ระบบใช้เวลานานเกินไป ลองใหม่อีกครั้ง")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="ระบบประมวลผลไม่พร้อมใช้งานชั่วคราว")

    created = _now()
    payload = {"request_id": h["X-Request-ID"], "session_id": session_id,
               "user_id": user["id"], "user_message_id": user_mid,
               "assistant_message_id": asst_mid, "user_message": body.message,
               "answer": data["answer"], "sources": data.get("sources", []),
               "route": data["route"], "engines_used": data.get("engines_used", []),
               "confidence": data.get("confidence"), "reasoning": data.get("reasoning"),
               "latency_ms": data.get("latency_ms"), "status": "ok",
               "created_at": created, "trace": data.get("trace")}
    bg.add_task(_send_log, payload, dict(h))                                # 10 ยิงหลังตอบ ไม่รอ

    return ChatResponse(                                                    # 9
        request_id=h["X-Request-ID"], session_id=session_id, message_id=asst_mid,
        answer=data["answer"], sources=data.get("sources", []), route=data["route"],
        engines_used=data.get("engines_used", []), confidence=data.get("confidence", 0.0),
        latency_ms=int((time.perf_counter() - t0) * 1000), created_at=created,
        trace=data.get("trace"))


async def _send_log(payload: dict, headers: dict) -> None:
    """ยิง log แบบไม่รอ + retry 2 ครั้ง — log หายแถวเดียวประวัติจะขาดถาวร
    แต่ถ้ายิงไม่ผ่านก็ห้ามทำให้ chat พัง แค่ log warning"""
    import asyncio
    async with httpx.AsyncClient() as c:
        for wait in (0, 1, 3):
            if wait:
                await asyncio.sleep(wait)
            try:
                await c.post(f"{RLOG}/log", headers=headers, json=payload, timeout=10)
                return
            except Exception as exc:
                last = exc
    jlog(event="log_failed", error=str(last))


# ---- ส่งต่อไป 07 ทั้งหมด ผู้ใช้เป็นใครเราบอก แต่ 07 เป็นคนตรวจว่า session เป็นของใคร ----
@app.get("/api/sessions")
async def sessions(access_token: str | None = Cookie(default=None)):
    user = _user_from_cookie(access_token)
    r = await _client.get(f"{RLOG}/sessions", headers=forward_headers(),
                          params={"user_id": user["id"]}, timeout=10)
    return r.json()


@app.get("/api/history/{session_id}")
async def history(session_id: str, access_token: str | None = Cookie(default=None)):
    user = _user_from_cookie(access_token)
    r = await _client.get(f"{RLOG}/history/{session_id}", headers=forward_headers(),
                          params={"user_id": user["id"], "limit": 50}, timeout=10)
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="ไม่พบบทสนทนานี้")
    return r.json()


@app.post("/api/feedback")
async def feedback(body: FeedbackRequest, access_token: str | None = Cookie(default=None)):
    user = _user_from_cookie(access_token)
    if body.rating not in (1, -1):
        raise HTTPException(status_code=422, detail="rating ต้องเป็น 1 หรือ -1")
    r = await _client.post(f"{RLOG}/feedback", headers=forward_headers(), timeout=10,
                           json={"message_id": body.message_id, "user_id": user["id"],
                                 "rating": body.rating, "comment": body.comment})
    return r.json()


@app.get("/api/stats")
async def stats(days: int = 7, access_token: str | None = Cookie(default=None)):
    _user_from_cookie(access_token)
    r = await _client.get(f"{RLOG}/stats", headers=forward_headers(),
                          params={"days": days}, timeout=10)
    return r.json()


@app.post("/api/upload")
async def upload():
    # STUB: replace -- ตรวจชนิดจริงด้วย python-magic, แปลง PDF ด้วย pdfplumber, เก็บ uploaded_files
    raise HTTPException(status_code=501, detail="ยังไม่รองรับการอัปโหลดในเวอร์ชัน stub")
