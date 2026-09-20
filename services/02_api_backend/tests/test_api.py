"""ชุดทดสอบ 02-api — แทนการไล่ยิง Swagger ด้วยมือทีละข้อ"""
from __future__ import annotations

import uuid
import time

from app import main
from .conftest import DEMO_PASSWORD, OTHER_SESSION, OWNED_SESSION

NEW_CHAT = {"session_id": None, "message": "ต่อไวไฟไม่ได้", "file_ids": []}


def assert_error_shape(response, status: int):
    assert response.status_code == status
    error = response.json()["error"]
    assert set(error) == {"code", "message", "service", "request_id"}
    assert error["service"] == "api"


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["service"] == "api"


def test_login_ok_sets_cookie(client):
    r = client.post("/api/auth/login", json={"username": "student", "password": DEMO_PASSWORD})
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "student"
    cookie = r.headers["set-cookie"]
    assert "access_token=" in cookie and "HttpOnly" in cookie


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"username": "student", "password": "ผิด"})
    assert_error_shape(r, 401)


def test_login_unknown_user(client):
    r = client.post("/api/auth/login", json={"username": "ไม่มีคนนี้", "password": "x"})
    assert_error_shape(r, 401)


def test_me_requires_login(client):
    assert_error_shape(client.get("/api/auth/me"), 401)


def test_logout_clears_cookie(logged_in):
    assert logged_in.post("/api/auth/logout").json() == {"ok": True}
    assert logged_in.get("/api/auth/me").status_code == 401


def test_unknown_path_uses_error_shape(client):
    assert_error_shape(client.get("/ไม่มีเส้นนี้"), 404)


# ---------- chat: ตรวจ input ----------
def test_chat_without_cookie(client):
    assert_error_shape(client.post("/api/chat", json=NEW_CHAT), 401)


def test_cookie_checked_before_body(client):
    r = client.post("/api/chat", json={"session_id": None, "message": "", "file_ids": []})
    assert_error_shape(r, 401)


def test_blank_message(logged_in):
    r = logged_in.post("/api/chat", json={**NEW_CHAT, "message": "   "})
    assert_error_shape(r, 422)


def test_session_id_must_be_uuid(logged_in):
    r = logged_in.post("/api/chat", json={**NEW_CHAT, "session_id": "abc"})
    assert_error_shape(r, 422)


def test_message_too_long(logged_in):
    r = logged_in.post("/api/chat", json={**NEW_CHAT, "message": "ก" * 4001})
    assert_error_shape(r, 422)


def test_new_chat(logged_in, upstream):
    r = logged_in.post("/api/chat", json=NEW_CHAT)
    assert r.status_code == 200
    body = r.json()
    uuid.UUID(body["session_id"])
    uuid.UUID(body["message_id"])
    assert body["route"] == "university_rag"
    assert body["confidence"] == 0.0
    assert body["trace"]["decided_at_layer"] == "rules"
    assert body["created_at"].endswith("+07:00")
    assert body["request_id"] == r.headers["x-request-id"]


def test_new_chat_skips_history(logged_in, upstream):
    logged_in.post("/api/chat", json=NEW_CHAT)
    assert not any(call.startswith("GET /history/") for call in upstream["calls"])


def test_followup_keeps_session_and_reads_history(logged_in, upstream):
    r = logged_in.post("/api/chat", json={**NEW_CHAT, "session_id": OWNED_SESSION})
    assert r.status_code == 200
    assert r.json()["session_id"] == OWNED_SESSION
    assert any(call.startswith("GET /history/") for call in upstream["calls"])
    assert upstream["route_request"]["history"] == [
        {"role": "user", "content": "ต่อไวไฟไม่ได้"},
    ]


def test_history_of_another_user(logged_in):
    r = logged_in.post("/api/chat", json={**NEW_CHAT, "session_id": OTHER_SESSION})
    assert_error_shape(r, 404)


def test_log_is_sent_after_answer(logged_in, upstream):
    logged_in.post("/api/chat", json=NEW_CHAT)
    assert "POST /log" in upstream["calls"]


def test_router_down(logged_in, upstream):
    upstream["router"] = "down"
    assert_error_shape(logged_in.post("/api/chat", json=NEW_CHAT), 502)


def test_router_timeout(logged_in, upstream):
    upstream["router"] = "timeout"
    assert_error_shape(logged_in.post("/api/chat", json=NEW_CHAT), 504)


def test_router_error(logged_in, upstream):
    upstream["router"] = "error"
    assert_error_shape(logged_in.post("/api/chat", json=NEW_CHAT), 502)


def test_chat_survives_when_response_log_is_down(logged_in, upstream):
    upstream["rlog"] = "down"
    r = logged_in.post("/api/chat", json={**NEW_CHAT, "session_id": OWNED_SESSION})
    assert r.status_code == 200
    assert r.json()["answer"]


def test_proxy_routes_ok(logged_in):
    assert logged_in.get("/api/sessions").status_code == 200
    assert logged_in.get(f"/api/history/{OWNED_SESSION}").status_code == 200
    assert logged_in.get("/api/stats?days=7").status_code == 200
    assert logged_in.post("/api/feedback", json={
        "message_id": str(uuid.uuid4()), "rating": 1, "comment": "ดี"}).status_code == 200


def test_proxy_routes_need_login(client):
    assert_error_shape(client.get("/api/sessions"), 401)
    assert_error_shape(client.get("/api/stats"), 401)


def test_proxy_returns_502_when_response_log_is_down(logged_in, upstream):
    upstream["rlog"] = "down"
    assert_error_shape(logged_in.get("/api/sessions"), 502)
    assert_error_shape(logged_in.get("/api/stats"), 502)


def test_history_of_another_user_via_proxy(logged_in):
    assert_error_shape(logged_in.get(f"/api/history/{OTHER_SESSION}"), 404)


def test_history_path_must_be_uuid(logged_in):
    assert_error_shape(logged_in.get("/api/history/abc"), 422)


def test_stats_days_must_be_at_least_one(logged_in):
    assert_error_shape(logged_in.get("/api/stats?days=0"), 422)


def test_feedback_rating_must_be_1_or_minus_1(logged_in):
    r = logged_in.post("/api/feedback", json={"message_id": str(uuid.uuid4()), "rating": 2})
    assert_error_shape(r, 422)


def test_rate_limit_blocks_after_quota(logged_in, monkeypatch):
    monkeypatch.setattr(main, "CHAT_RATE_LIMIT", 3)
    for _ in range(3):
        assert logged_in.post("/api/chat", json=NEW_CHAT).status_code == 200
    r = logged_in.post("/api/chat", json=NEW_CHAT)
    assert_error_shape(r, 429)
    assert int(r.headers["retry-after"]) > 0


def test_rate_limit_is_per_user(logged_in, monkeypatch):
    monkeypatch.setattr(main, "CHAT_RATE_LIMIT", 2)
    for _ in range(2):
        logged_in.post("/api/chat", json=NEW_CHAT)
    assert logged_in.post("/api/chat", json=NEW_CHAT).status_code == 429
    main._rate_hits.clear()                      # เหมือนมีผู้ใช้อีกคนที่ยังไม่ได้ถาม
    assert logged_in.post("/api/chat", json=NEW_CHAT).status_code == 200


def test_rate_limit_window_expires(logged_in, monkeypatch):
    monkeypatch.setattr(main, "CHAT_RATE_LIMIT", 1)
    monkeypatch.setattr(main, "RATE_WINDOW", 0.2)
    assert logged_in.post("/api/chat", json=NEW_CHAT).status_code == 200
    assert logged_in.post("/api/chat", json=NEW_CHAT).status_code == 429
    time.sleep(0.25)
    assert logged_in.post("/api/chat", json=NEW_CHAT).status_code == 200