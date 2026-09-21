"""รูปแบบข้อมูลตาม docs/CONTRACT.md ข้อ 6 — ห้ามเปลี่ยนชื่อ field"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0


class LogEntry(BaseModel):
    request_id: str
    session_id: str
    user_id: str
    user_message_id: str
    assistant_message_id: str
    user_message: str
    answer: str
    sources: list[dict] = Field(default_factory=list)
    route: str
    engines_used: list[str] = Field(default_factory=list)
    confidence: float | None = None
    reasoning: str | None = None
    latency_ms: int | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    status: Literal["ok", "error"] = "ok"
    error_code: str | None = None
    created_at: str | None = None
    trace: dict[str, Any] | None = None


class FeedbackIn(BaseModel):
    message_id: str
    user_id: str
    rating: Literal[1, -1]
    comment: str | None = None


class Message(BaseModel):
    message_id: str
    role: Literal["user", "assistant"]
    content: str
    sources: list[dict] = Field(default_factory=list)
    route: str | None = None
    rating: int | None = None
    created_at: str | None = None
