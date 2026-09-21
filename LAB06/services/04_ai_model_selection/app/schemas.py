"""รูปแบบข้อมูลตาม docs/CONTRACT.md ข้อ 3 — ห้ามเปลี่ยนชื่อ field"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class GeneralRequest(BaseModel):
    request_id: str
    query: str
    history: list[HistoryMessage] = Field(default_factory=list)
    file_text: str | None = None
    task: Literal["qa", "summarize", "write"] = "qa"


class ClassifyRequest(BaseModel):
    request_id: str
    text: str


class EngineResult(BaseModel):
    engine: Literal["general_ai", "local_ai"]
    content: str
    data: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict] = Field(default_factory=list)
    model: str
    latency_ms: int
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
