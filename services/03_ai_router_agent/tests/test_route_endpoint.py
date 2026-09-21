"""ทดสอบ /route ทั้งเส้นในระดับ HTTP — โดยเฉพาะ "ของที่คนอื่นอ่านต่อ"

payload ที่ใช้ในไฟล์นี้คัดลอกมาจากสิ่งที่ 02 api ส่งจริง (services/02_api_backend/app/main.py)
ไม่ได้แต่งขึ้นเอง — ถ้าฝั่งใดฝั่งหนึ่งเปลี่ยน ไฟล์นี้ต้องแดง
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import cascade, clients  # noqa: E402
from app.main import app  # noqa: E402

# 02 ส่งแค่ 5 field นี้ ไม่มี file_text และ user ไม่มี faculty
API_PAYLOAD = {
    "request_id": "11111111-1111-1111-1111-111111111111",
    "session_id": "22222222-2222-2222-2222-222222222222",
    "user": {"id": "33333333-3333-3333-3333-333333333333", "role": "student"},
    "query": "ต่อไวไฟไม่ได้ ควรไล่ตรวจอะไรก่อน",
    "history": [],
}


@pytest.fixture
def client(monkeypatch):
    async def no_network(*args, **kwargs):
        raise clients.HopError("hop", "ปิดไว้ในเทส")

    for name in ("classify", "search", "general", "generate"):
        monkeypatch.setattr(clients, name, no_network)
    with TestClient(app) as c:
        yield c


def test_health_matches_contract(client):
    body = client.get("/health").json()
    assert set(body) == {"status", "service", "version"}
    assert body["status"] == "ok"


def test_route_accepts_exactly_what_api_sends(client):
    resp = client.post("/route", json=API_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    # 02 อ่าน answer/route ตรง ๆ และ .get() ที่เหลือ — ขาดสองตัวแรกเมื่อไหร่ 02 พังทันที
    for field in ("request_id", "answer", "sources", "route", "engines_used",
                  "confidence", "reasoning", "latency_ms", "token_usage", "trace"):
        assert field in body, field
    assert body["route"] in ("general_ai", "university_rag", "local_ai", "clarify", "decline")
    assert body["request_id"] == API_PAYLOAD["request_id"]


def test_trace_shape_is_what_the_web_renders(client):
    trace = client.post("/route", json=API_PAYLOAD).json()["trace"]
    # 01 อ่าน decided_at_layer, steps[].name, steps[].ms และ fallback มาที่ trace.reasoning
    assert trace["decided_at_layer"] in ("guard", "rules", "classifier", "llm")
    assert all({"name", "ms"} <= set(step) for step in trace["steps"])
    assert trace["reasoning"]


def test_request_id_header_is_echoed(client):
    resp = client.post("/route", json=API_PAYLOAD, headers={"X-Request-ID": "trace-me"})
    assert resp.headers["X-Request-ID"] == "trace-me"


def test_unexpected_error_uses_contract_error_shape(client, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("อะไรสักอย่างพังโดยไม่ได้ตั้งใจ")

    monkeypatch.setattr(cascade, "decide", boom)
    resp = client.post("/route", json=API_PAYLOAD)
    # hop ล่มเรามี fallback ให้แล้ว ส่วน error ที่ไม่ได้คาดไว้ต้องโผล่ออกมาเป็น 500 ตาม CONTRACT ข้อ 0
    # กลบเป็น 200 แล้วจะกลายเป็นบั๊กเงียบที่ไม่มีใครเห็นตอนรวมงาน
    assert resp.status_code == 500
    err = resp.json()["error"]
    assert err["code"] == "INTERNAL_ERROR"
    assert err["service"] == "router" and err["request_id"]


def test_validation_error_uses_contract_error_shape(client):
    resp = client.post("/route", json={"request_id": "1"})      # ส่ง field ไม่ครบ
    assert resp.status_code == 422
    err = resp.json()["error"]
    # FastAPI ตอบ {"detail": [...]} มาเอง ซึ่งคนละรูปแบบกับที่ทั้งทีมตกลงกันไว้
    assert err["code"] == "VALIDATION_ERROR"
    assert err["service"] == "router"


def test_content_type_declares_utf8(client):
    resp = client.post("/route", json=API_PAYLOAD)
    assert resp.headers["content-type"] == "application/json; charset=utf-8"
    assert "ขอ" in resp.text or "ระบบ" in resp.text          # ภาษาไทยต้องไม่เพี้ยน


def test_empty_query_is_rejected_gracefully(client):
    body = client.post("/route", json={**API_PAYLOAD, "query": "   "}).json()
    assert body["route"] == "clarify"
    assert body["trace"]["decided_at_layer"] == "guard"
