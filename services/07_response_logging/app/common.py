"""ของกลางที่ทุก service ต้องมีเหมือนกัน

สามอย่างในไฟล์นี้เป็นข้อบังคับจาก docs/CONTRACT.md ข้อ 0
  1. GET /health ตอบรูปแบบเดียวกันทุกตัว (compose ใช้เช็กว่าพร้อมรับงานหรือยัง)
  2. X-Request-ID รับมาถ้ามี ไม่มีก็สร้างใหม่ แล้ว **ส่งต่อทุกครั้งที่เรียก service อื่น**
  3. log เป็น JSON บรรทัดเดียวต่อหนึ่ง request พร้อม request_id
     เวลารวมงานแล้วพัง จะไล่ได้ว่า request เดียวกันไปตายที่ hop ไหน
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar

from fastapi import Request
from fastapi.responses import JSONResponse

SERVICE_NAME = os.getenv("SERVICE_NAME", "response-log")
VERSION = os.getenv("GIT_SHA", "0.1.0")

# เก็บ request id ไว้ให้โค้ดส่วนอื่นหยิบใช้ได้ โดยไม่ต้องส่งผ่านทุกฟังก์ชัน
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
log = logging.getLogger(SERVICE_NAME)
log.setLevel(os.getenv("LOG_LEVEL", "INFO"))
log.handlers = [_handler]


def jlog(**fields) -> None:
    """เขียน log เป็น JSON หนึ่งบรรทัด — อย่าใช้ print()"""
    log.info(json.dumps({"service": SERVICE_NAME,
                         "request_id": request_id_ctx.get(),
                         **fields}, ensure_ascii=False))


def health_payload() -> dict:
    return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}


def forward_headers() -> dict:
    """ใส่ใน header ทุกครั้งที่เรียก service อื่น ไม่งั้นสายจะขาดตรงนั้น"""
    return {"X-Request-ID": request_id_ctx.get()}


def error_body(code: str, message: str) -> dict:
    """รูปแบบ error เดียวกันทุก service ตาม CONTRACT ข้อ 0"""
    return {"error": {"code": code, "message": message,
                      "service": SERVICE_NAME, "request_id": request_id_ctx.get()}}


async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_id_ctx.set(rid)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        jlog(method=request.method, path=request.url.path, status=500,
             latency_ms=int((time.perf_counter() - started) * 1000), error=str(exc))
        return JSONResponse(status_code=500,
                            content=error_body("INTERNAL_ERROR", "เกิดข้อผิดพลาดภายในระบบ"))
    response.headers["X-Request-ID"] = rid
    jlog(method=request.method, path=request.url.path, status=response.status_code,
         latency_ms=int((time.perf_counter() - started) * 1000))
    return response
