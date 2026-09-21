"""รูปแบบข้อมูลตาม docs/CONTRACT.md ข้อ 5 — ห้ามเปลี่ยนชื่อ field"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0


class Source(BaseModel):
    ref: int
    doc_id: str
    title: str
    url: str | None = None
    page: int | None = None
    date: str | None = None
    category: str = "other"


class Context(BaseModel):
    ref: int
    text: str
    source: Source


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class GenerateRequest(BaseModel):
    request_id: str
    mode: Literal["grounded", "passthrough", "explain_local"]
    query: str = ""
    history: list[HistoryMessage] = Field(default_factory=list)
    contexts: list[Context] = Field(default_factory=list)
    draft: str | None = None


class GenerateResponse(BaseModel):
    request_id: str
    answer: str
    sources: list[Source] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    model: str
    latency_ms: int
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
