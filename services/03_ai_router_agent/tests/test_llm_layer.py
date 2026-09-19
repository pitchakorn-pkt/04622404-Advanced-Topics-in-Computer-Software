"""ชั้น 3: การ parse JSON และ fallback provider

fallback provider ไม่ใช่ของประดับ — แผนของทีม (docs/00_PLAN_OVERVIEW.md ข้อ 154) เขียนไว้ว่า
"ต้องทำจริงและทดสอบจริง" เพราะ free tier ของ Groq จำกัดคำขอต่อนาที และเราใช้กันแปดคน
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import llm  # noqa: E402


class FakeCompletions:
    def __init__(self, content: str | None, error: Exception | None = None):
        self.content = content
        self.error = error
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error

        class Msg:  # โครงเท่าที่โค้ดเราหยิบใช้จริงจาก response ของ openai
            content = self.content

        class Choice:
            message = Msg()

        class Usage:
            prompt_tokens, completion_tokens = 11, 22

        class Resp:
            choices = [Choice()]
            usage = Usage()

        return Resp()


class FakeClient:
    def __init__(self, completions: FakeCompletions):
        self.chat = type("Chat", (), {"completions": completions})()


def wire(monkeypatch, providers: dict[str, FakeCompletions]):
    """ผูก provider ปลอมเข้ากับ llm._client โดยเรียงลำดับตาม LLM_PRIMARY / LLM_FALLBACK"""
    def fake_client(name: str):
        if name not in providers:
            return None
        return FakeClient(providers[name]), f"model-{name}"

    monkeypatch.setattr(llm, "_client", fake_client)
    monkeypatch.setattr(llm, "LLM_PRIMARY", "groq")
    monkeypatch.setattr(llm, "LLM_FALLBACK", "gemini")


GOOD_JSON = '{"route": "university_rag", "confidence": 0.82, "reasoning": "เป็นปัญหาไวไฟ", "rewritten_query": "ต่อไวไฟไม่ได้"}'


def test_uses_primary_provider_when_it_works(monkeypatch):
    primary = FakeCompletions(GOOD_JSON)
    fallback = FakeCompletions(GOOD_JSON)
    wire(monkeypatch, {"groq": primary, "gemini": fallback})

    verdict = asyncio.run(llm.decide_route("ต่อไวไฟไม่ได้", []))
    assert verdict.route == "university_rag"
    assert verdict.model == "model-groq"
    assert verdict.token_usage == (11, 22)
    assert fallback.calls == 0          # ตัวหลักตอบได้ ห้ามไปกวนตัวสำรอง


def test_falls_back_to_second_provider(monkeypatch):
    primary = FakeCompletions(None, error=RuntimeError("429 rate limit"))
    fallback = FakeCompletions(GOOD_JSON)
    wire(monkeypatch, {"groq": primary, "gemini": fallback})

    verdict = asyncio.run(llm.decide_route("ต่อไวไฟไม่ได้", []))
    assert verdict is not None and verdict.model == "model-gemini"
    assert primary.calls == 1 and fallback.calls == 1


def test_returns_none_when_every_provider_fails(monkeypatch):
    wire(monkeypatch, {"groq": FakeCompletions(None, error=RuntimeError("ล่ม")),
                       "gemini": FakeCompletions(None, error=RuntimeError("ล่มอีก"))})
    # คืน None เพื่อให้ cascade ถอยไป clarify — ห้ามโยน exception ออกไป
    assert asyncio.run(llm.decide_route("ต่อไวไฟไม่ได้", [])) is None


def test_no_provider_configured_is_not_an_error(monkeypatch):
    wire(monkeypatch, {})               # ยังไม่ได้ใส่ API key ใน .env
    assert asyncio.run(llm.decide_route("ต่อไวไฟไม่ได้", [])) is None


@pytest.mark.parametrize("raw", [
    "ไม่ใช่ JSON เลย",
    '{"route": "ไปไหนก็ได้", "confidence": 0.9}',      # route นอกเหนือ 5 ค่าที่ contract อนุญาต
    '{"confidence": 0.9}',                              # ไม่มี route
    "",
])
def test_bad_llm_output_returns_none_instead_of_crashing(monkeypatch, raw):
    wire(monkeypatch, {"groq": FakeCompletions(raw)})
    assert asyncio.run(llm.decide_route("คำถาม", [])) is None


def test_json_wrapped_in_text_is_still_parsed(monkeypatch):
    wire(monkeypatch, {"groq": FakeCompletions(f"นี่คือคำตอบครับ {GOOD_JSON} จบแล้ว")})
    verdict = asyncio.run(llm.decide_route("ต่อไวไฟไม่ได้", []))
    assert verdict is not None and verdict.route == "university_rag"


def test_confidence_is_clamped(monkeypatch):
    wire(monkeypatch, {"groq": FakeCompletions('{"route": "general_ai", "confidence": 7}')})
    assert asyncio.run(llm.decide_route("คำถาม", [])).confidence == 1.0


def test_rewrite_returns_original_when_nothing_changed(monkeypatch):
    wire(monkeypatch, {"groq": FakeCompletions('{"rewritten_query": "คำถามเดิม"}')})
    rewritten, _tokens = asyncio.run(llm.rewrite_query("คำถามเดิม", [{"role": "user", "content": "ก่อนหน้า"}]))
    assert rewritten is None            # เหมือนเดิม = ไม่ต้องเปลี่ยนคำค้น
