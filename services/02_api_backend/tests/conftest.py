"""ของกลางสำหรับเทส — จำลอง router, 07 และฐานข้อมูล จึงรันได้โดยไม่ต้องเปิด container"""
from __future__ import annotations

import json
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main

OWNED_SESSION = "11111111-1111-1111-1111-111111111111"
OTHER_SESSION = "22222222-2222-2222-2222-222222222222"

DEMO_PASSWORD = "student"
DEMO_USER = {
    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "student")),
    "username": "student",
    "display_name": "student",
    "role": "student",
    "password_hash": "ไม่ได้ใช้ เพราะ verify_password ถูกแทนแล้ว",
}


class FakeUser:
    def __init__(self, data: dict):
        for key, value in data.items():
            setattr(self, key, value)


@pytest.fixture
def upstream():
    """ปรับพฤติกรรมของ router และ 07 ในแต่ละเทสผ่าน dict นี้"""
    return {"router": "ok", "rlog": "ok", "calls": []}


def _handler(state):
    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        state["calls"].append(f"{request.method} {path}")

        if request.url.host == "router":
            mode = state["router"]
            if mode == "down":
                raise httpx.ConnectError("router ไม่ตอบ", request=request)
            if mode == "timeout":
                raise httpx.ReadTimeout("router ช้าเกินไป", request=request)
            if mode == "error":
                return httpx.Response(500, text="boom")
            body = json.loads(request.content)
            state["route_request"] = body
            return httpx.Response(200, json={
                "request_id": body["request_id"], "answer": "ลองปิดเปิดไวไฟดูครับ [1]",
                "sources": [], "route": "university_rag",
                "engines_used": ["retrieval", "generation"],
                "confidence": None,                       # จงใจส่ง null มาทดสอบ
                "reasoning": "ชั้น rules", "latency_ms": 120,
                "token_usage": {"input": 10, "output": 20},
                "trace": {"decided_at_layer": "rules", "steps": []},
            })

        mode = state["rlog"]
        if mode == "down":
            raise httpx.ConnectError("07 ไม่ตอบ", request=request)
        if path.startswith("/history/"):
            if path.endswith(OTHER_SESSION):
                return httpx.Response(404, json={})
            return httpx.Response(200, json={"session_id": OWNED_SESSION, "messages": [
                {"message_id": str(uuid.uuid4()), "role": "user", "content": "ต่อไวไฟไม่ได้",
                 "sources": [], "route": None, "rating": None, "created_at": "x"},
            ]})
        if path == "/log":
            return httpx.Response(202, json={"accepted": True})
        if path == "/sessions":
            return httpx.Response(200, json={"sessions": []})
        if path == "/feedback":
            return httpx.Response(200, json={"ok": True})
        if path == "/stats":
            return httpx.Response(200, json={"total_requests": 0})
        return httpx.Response(404, json={})

    return handle


@pytest.fixture
def client(monkeypatch, upstream):
    async def fake_init_db():
        return 0

    async def fake_get_user(username: str):
        return FakeUser(DEMO_USER) if username == "student" else None

    def fake_verify(password: str, hashed: str) -> bool:
        return password == DEMO_PASSWORD

    monkeypatch.setattr(main, "init_db", fake_init_db)
    monkeypatch.setattr(main, "get_user", fake_get_user)
    monkeypatch.setattr(main, "verify_password", fake_verify)

    with TestClient(main.app) as test_client:
        main._client = httpx.AsyncClient(transport=httpx.MockTransport(_handler(upstream)))
        yield test_client


@pytest.fixture
def logged_in(client):
    r = client.post("/api/auth/login", json={"username": "student", "password": DEMO_PASSWORD})
    assert r.status_code == 200
    return client
