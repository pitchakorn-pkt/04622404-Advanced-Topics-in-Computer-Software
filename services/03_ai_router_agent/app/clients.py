"""ตัวเรียก service เพื่อนบ้าน — 04 engines, 05 retrieval, 06 generation

กติกาสามข้อที่ทุกฟังก์ชันในไฟล์นี้ทำเหมือนกัน
  1. ส่ง X-Request-ID ต่อทุกครั้ง ไม่งั้นสายจะขาดตรง hop นั้นตอนไล่ log
  2. มี timeout เสมอ และ timeout ที่ใช้จริงมาจาก Budget ไม่ใช่เพดานต่อ hop ตรง ๆ
  3. ล้มแล้วโยน HopError ที่บอกชื่อ hop — คนเรียกจะได้เลือก fallback ได้ ไม่ใช่ทั้ง request พังไปด้วย
"""
from __future__ import annotations

from typing import Any

import httpx

from .common import forward_headers, jlog
from .config import ENGINES_URL, GENERATION_URL, RETRIEVAL_URL


class HopError(Exception):
    """hop หนึ่งล้ม แต่ request ยังไปต่อได้ด้วยเส้นสำรอง"""

    def __init__(self, hop: str, reason: str) -> None:
        super().__init__(f"{hop}: {reason}")
        self.hop = hop
        self.reason = reason


async def _post(client: httpx.AsyncClient, url: str, payload: dict,
                timeout: float, hop: str) -> dict:
    try:
        resp = await client.post(url, json=payload, headers=forward_headers(), timeout=timeout)
    except httpx.TimeoutException as exc:
        jlog(event="hop_timeout", hop=hop, timeout=timeout)
        raise HopError(hop, f"timeout {timeout:.1f}s") from exc
    except httpx.HTTPError as exc:
        jlog(event="hop_error", hop=hop, error=str(exc))
        raise HopError(hop, str(exc)) from exc

    if resp.status_code >= 400:
        jlog(event="hop_status", hop=hop, status=resp.status_code)
        raise HopError(hop, f"HTTP {resp.status_code}")

    try:
        return resp.json()
    except ValueError as exc:
        raise HopError(hop, "ตอบกลับไม่ใช่ JSON") from exc


async def search(client: httpx.AsyncClient, request_id: str, query: str,
                 top_k: int, timeout: float, filters: dict | None = None) -> list[dict]:
    """คืน chunks — list ว่างแปลว่า "ไม่เจอ" ไม่ใช่ error (CONTRACT ข้อ 4)"""
    payload: dict[str, Any] = {"request_id": request_id, "query": query, "top_k": top_k}
    if filters:
        payload["filters"] = filters
    data = await _post(client, f"{RETRIEVAL_URL}/search", payload, timeout, "retrieval.search")
    return data.get("chunks") or []


async def classify(client: httpx.AsyncClient, request_id: str, text: str,
                   timeout: float) -> dict:
    return await _post(client, f"{ENGINES_URL}/local/classify",
                       {"request_id": request_id, "text": text}, timeout, "engines.classify")


async def general(client: httpx.AsyncClient, request_id: str, query: str,
                  history: list[dict], timeout: float, task: str = "qa",
                  file_text: str | None = None) -> dict:
    payload: dict[str, Any] = {"request_id": request_id, "query": query,
                               "history": history, "task": task}
    if file_text:
        payload["file_text"] = file_text
    return await _post(client, f"{ENGINES_URL}/general", payload, timeout, "engines.general")


async def generate(client: httpx.AsyncClient, request_id: str, mode: str, query: str,
                   timeout: float, history: list[dict] | None = None,
                   contexts: list[dict] | None = None, draft: str | None = None) -> dict:
    payload: dict[str, Any] = {"request_id": request_id, "mode": mode, "query": query,
                               "history": history or []}
    if contexts is not None:
        payload["contexts"] = contexts
    if draft is not None:
        payload["draft"] = draft
    return await _post(client, f"{GENERATION_URL}/generate", payload, timeout,
                       f"generation.{mode}")
