"""รูปแบบข้อมูลตาม docs/CONTRACT.md ข้อ 2 — ห้ามเปลี่ยนชื่อ field"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Route = Literal["general_ai", "university_rag", "local_ai", "clarify", "decline"]


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class RouteUser(BaseModel):
    id: str
    role: str = "student"
    faculty: str | None = None


class RouteRequest(BaseModel):
    request_id: str
    session_id: str
    user: RouteUser
    query: str
    history: list[HistoryMessage] = Field(default_factory=list)
    file_text: str | None = None


class Trace(BaseModel):
    decided_at_layer: Literal["guard", "rules", "classifier", "llm"]
    steps: list[dict[str, Any]] = Field(default_factory=list)


class RouteResponse(BaseModel):
    request_id: str
    answer: str
    sources: list[dict] = Field(default_factory=list)
    route: Route
    engines_used: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    latency_ms: int = 0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    trace: Trace | None = None
