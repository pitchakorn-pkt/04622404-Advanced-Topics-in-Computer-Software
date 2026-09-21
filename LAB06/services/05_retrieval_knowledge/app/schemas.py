"""รูปแบบข้อมูลตาม docs/CONTRACT.md ข้อ 4 — ห้ามเปลี่ยนชื่อ field"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["it_support", "howto", "faq", "policy", "other"]


class Source(BaseModel):
    ref: int
    doc_id: str
    title: str
    url: str | None = None
    page: int | None = None
    date: str | None = None
    category: Category = "other"


class Chunk(BaseModel):
    chunk_id: str
    text: str
    score: float
    bm25_score: float | None = None
    vector_score: float | None = None
    source: Source


class SearchFilters(BaseModel):
    category: Category | None = None
    year_from: int | None = None


class SearchRequest(BaseModel):
    request_id: str
    query: str
    top_k: int = 5
    filters: SearchFilters | None = None


class SearchResponse(BaseModel):
    request_id: str
    chunks: list[Chunk] = Field(default_factory=list)
    latency_ms: int
