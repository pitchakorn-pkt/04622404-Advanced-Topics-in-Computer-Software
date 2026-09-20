"""02 API / Backend — ประตูหน้าบ้าน"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta, timezone
import asyncio
import httpx
import jwt

from uuid import UUID

from fastapi import BackgroundTasks, Cookie, Depends, FastAPI, HTTPException, Query, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from contextlib import asynccontextmanager

from .common import error_body, forward_headers, health_payload, jlog, request_id_middleware  # noqa: F401
from .db import engine, get_user, init_db, verify_password
from .schemas import ChatRequest, ChatResponse, FeedbackRequest, LoginRequest

ROUTER = os.getenv("ROUTER_URL", "http://router:8000")
RLOG = os.getenv("RESPONSE_LOG_URL", "http://response-log:8000")
SECRET = os.getenv("JWT_SECRET_KEY", "dev-only-change-me")
T_ROUTER = 75.0   # ต้องมากกว่างบรวมของ router (70s) ตาม CONTRACT ข้อ 0
T_RLOG = 5.0
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "10"))
RATE_WINDOW = float(os.getenv("CHAT_RATE_WINDOW", "60"))

ERROR_CODES = {
    400: "BAD_REQUEST", 401: "UNAUTHORIZED", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED",
    413: "FILE_TOO_LARGE", 422: "VALIDATION_ERROR", 429: "RATE_LIMITED",
    500: "INTERNAL_ERROR", 501: "NOT_IMPLEMENTED", 502: "UPSTREAM_UNAVAILABLE",
    504: "UPSTREAM_TIMEOUT",
}

_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan(_: FastAPI):
    global _client
    _client = httpx.AsyncClient()
    seeded = await init_db()
    jlog(event="db_ready", seeded_users=seeded)
    try:
        yield
    finally:
        await _client.aclose()
        await engine.dispose()

app = FastAPI(title="chuayduay · api", lifespan=lifespan)
app.middleware("http")(request_id_middleware)

@app.exception_handler(StarletteHTTPException)
async def _http_error(request, exc: StarletteHTTPException):
    code = ERROR_CODES.get(exc.status_code, "ERROR")
    return JSONResponse(status_code=exc.status_code, headers=getattr(exc, "headers", None),
                        content=error_body(code, str(exc.detail)))


@app.exception_handler(RequestValidationError)
async def _validation_error(request, exc: RequestValidationError):
    fields = sorted({str(e["loc"][-1]) for e in exc.errors()})
    return JSONResponse(status_code=422, content=error_body(
        "VALIDATION_ERROR", f"ข้อมูลไม่ถูกต้อง: {', '.join(fields)}"))

BKK = timezone(timedelta(hours=7))

def _now() -> str:
    return datetime.now(BKK).isoformat(timespec="seconds")

async def _user_from_cookie(access_token: str | None = Cookie(default=None)) -> dict:
    if not access_token:
        raise HTTPException(status_code=401, detail="ยังไม่ได้เข้าสู่ระบบ")
    try:
        return jwt.decode(access_token, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="เซสชันหมดอายุ")


@app.get("/health")
async def health():
    return health_payload()


@app.post("/api/auth/login")
async def login(body: LoginRequest, response: Response):
    row = await get_user(body.username)
    if row is None or not verify_password(body.password, row.password_hash):
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    user = {"id": str(row.id), "username": row.username,
            "display_name": row.display_name, "role": row.role}
    token = jwt.encode(user, SECRET, algorithm="HS256")
    response.set_cookie("access_token", token, httponly=True, samesite="lax", path="/")
    return {"user": user}


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@app.get("/api/auth/me")
async def me(user: dict = Depends(_user_from_cookie)):
    return {"user": user}

_rate_hits: dict[str, list[float]] = {}


def _check_rate_limit(user_id: str) -> None:
    now = time.monotonic()
    hits = [t for t in _rate_hits.get(user_id, []) if now - t < RATE_WINDOW]
    if len(hits) >= CHAT_RATE_LIMIT:
        _rate_hits[user_id] = hits
        retry_after = int(RATE_WINDOW - (now - hits[0])) + 1
        raise HTTPException(status_code=429,
                            detail=f"ถามถี่เกินไป ลองใหม่อีกครั้งในอีก {retry_after} วินาที",
                            headers={"Retry-After": str(retry_after)})
    hits.append(now)
    _rate_hits[user_id] = hits

@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, bg: BackgroundTasks,
               user: dict = Depends(_user_from_cookie)):                    # 1
    t0 = time.perf_counter()
    _check_rate_limit(user["id"])                                           # 2
    assert _client is not None
    h = forward_headers()
    session_id = str(body.session_id) if body.session_id else str(uuid.uuid4())                       # 3 (07 สร้างแถวให้เอง)
    user_mid, asst_mid = str(uuid.uuid4()), str(uuid.uuid4())               # 7

    history: list[dict] = []                                                # 4
    if body.session_id:                     # session ใหม่ยังไม่มีประวัติ ไม่ต้องถาม 07
        try:
            r = await _client.get(f"{RLOG}/history/{session_id}", headers=h, timeout=T_RLOG,
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
    confidence = data.get("confidence")
    confidence = float(confidence) if isinstance(confidence, (int, float)) else 0.0
    payload = {"request_id": h["X-Request-ID"], "session_id": session_id,
               "user_id": user["id"], "user_message_id": user_mid,
               "assistant_message_id": asst_mid, "user_message": body.message,
               "answer": data["answer"], "sources": data.get("sources", []),
               "route": data["route"], "engines_used": data.get("engines_used", []),
               "confidence": confidence, "reasoning": data.get("reasoning"),
               "latency_ms": data.get("latency_ms"),
               "token_usage": data.get("token_usage") or {"input": 0, "output": 0},
               "status": "ok", "error_code": None,
               "created_at": created, "trace": data.get("trace")}
    bg.add_task(_send_log, payload, dict(h))                                # 10 ยิงหลังตอบ ไม่รอ

    return ChatResponse(                                                    # 9
        request_id=h["X-Request-ID"], session_id=session_id, message_id=asst_mid,
        answer=data["answer"], sources=data.get("sources", []), route=data["route"],
        engines_used=data.get("engines_used", []), confidence=confidence,
        latency_ms=int((time.perf_counter() - t0) * 1000), created_at=created,
        trace=data.get("trace"))


async def _send_log(payload: dict, headers: dict) -> None:
    """ยิง log แบบไม่รอ + retry 2 ครั้ง — log หายแถวเดียวประวัติจะขาดถาวร
    แต่ถ้ายิงไม่ผ่านก็ห้ามทำให้ chat พัง แค่ log warning"""
    last = ""
    for wait in (0, 1, 3):
        if wait:
            await asyncio.sleep(wait)
        try:
            r = await _client.post(f"{RLOG}/log", headers=headers, json=payload, timeout=T_RLOG)
        except httpx.HTTPError as exc:
            last = type(exc).__name__
            continue
        if r.status_code < 400:
            return
        last = f"HTTP {r.status_code}"
        if r.status_code < 500 and r.status_code != 429:
            break
    jlog(event="log_failed", error=last, session_id=payload["session_id"],
         message_id=payload["assistant_message_id"])

async def _rlog(method: str, path: str, *, params: dict | None = None,
                json: dict | None = None, not_found: str = "ไม่พบข้อมูล") -> dict:
    try:
        r = await _client.request(method, f"{RLOG}{path}", params=params, json=json,
                                  headers=forward_headers(), timeout=T_RLOG)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="ระบบประวัติใช้เวลานานเกินไป")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="ระบบประวัติไม่พร้อมใช้งานชั่วคราว")
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail=not_found)
    if r.status_code >= 400:
        jlog(event="response_log_error", path=path, upstream_status=r.status_code)
        raise HTTPException(status_code=502, detail="ระบบประวัติไม่พร้อมใช้งานชั่วคราว")
    try:
        return r.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="ระบบประวัติตอบกลับไม่ถูกต้อง")

# ---- ส่งต่อไป 07 ทั้งหมด ผู้ใช้เป็นใครเราบอก แต่ 07 เป็นคนตรวจว่า session เป็นของใคร ----
@app.get("/api/sessions")
async def sessions(user: dict = Depends(_user_from_cookie)):
    return await _rlog("GET", "/sessions", params={"user_id": user["id"]})


@app.get("/api/history/{session_id}")
async def history(session_id: UUID, user: dict = Depends(_user_from_cookie)):
    return await _rlog("GET", f"/history/{session_id}",
                       params={"user_id": user["id"], "limit": 50},
                       not_found="ไม่พบบทสนทนานี้")


@app.post("/api/feedback")
async def feedback(body: FeedbackRequest, user: dict = Depends(_user_from_cookie)):
    return await _rlog("POST", "/feedback", json={
        "message_id": str(body.message_id), "user_id": user["id"],
        "rating": body.rating, "comment": body.comment})


@app.get("/api/stats")
async def stats(days: int = Query(7, ge=1), user: dict = Depends(_user_from_cookie)):
    return await _rlog("GET", "/stats", params={"days": days})


@app.post("/api/upload")
async def upload():
    # STUB: replace -- ตรวจชนิดจริงด้วย python-magic, แปลง PDF ด้วย pdfplumber, เก็บ uploaded_files
    raise HTTPException(status_code=501, detail="ยังไม่รองรับการอัปโหลดในเวอร์ชัน stub")
