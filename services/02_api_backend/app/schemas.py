"""รูปแบบข้อมูลตาม docs/CONTRACT.md ข้อ 1 — ห้ามเปลี่ยนชื่อ field"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)
    file_ids: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    request_id: str
    session_id: str
    message_id: str
    answer: str
    sources: list[dict] = Field(default_factory=list)
    route: str
    engines_used: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    latency_ms: int = 0
    created_at: str
    trace: dict[str, Any] | None = None


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int
    comment: str | None = None
