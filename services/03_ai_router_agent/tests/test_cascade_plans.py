"""ชั้น 2-3 และ execution plan — ทดสอบโดยแทนที่ hop ด้วยของปลอม

ไม่ยิง service จริงในไฟล์นี้ เพราะสิ่งที่ต้องพิสูจน์คือ "เราเรียกใครด้วยอะไร และถ้าเขาล่มเราทำอะไร"
ไม่ใช่ว่าเพื่อนตอบถูกไหม เคสที่เก็บไว้ที่นี่คือเคสที่เคยทำให้ระบบแบบนี้พังเงียบ:
chunks ว่าง, retrieval ล่ม, LLM ตอบ JSON เพี้ยน, และงบเวลาหมดกลางทาง
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import cascade, clients, llm, plans  # noqa: E402
from app.budget import Budget, Steps  # noqa: E402

CHUNK = {
    "chunk_id": "it-wifi-001#p1#c1",
    "text": "ขั้นแรกให้ลืมเครือข่ายแล้วเชื่อมใหม่",
    "score": 0.81,
    "source": {"ref": 99, "doc_id": "it-wifi-001", "title": "ต่อ Wi-Fi ไม่ได้", "category": "it_support"},
}


def run(coro):
    return asyncio.run(coro)


def engine_result(content: str, label: str = "connectivity", score: float = 0.9) -> dict:
    return {"engine": "local_ai", "content": content,
            "data": {"label": label, "score": score},
            "model": "intent_v1", "latency_ms": 5,
            "token_usage": {"input": 10, "output": 5}}


@pytest.fixture
def calls(monkeypatch):
    """บันทึกว่าเราเรียก hop ไหนด้วย argument อะไรบ้าง"""
    seen: dict[str, list] = {"classify": [], "search": [], "general": [], "generate": []}

    async def fake_classify(client, request_id, text, timeout):
        seen["classify"].append(text)
        return engine_result("หมวด: connectivity (0.90)")

    async def fake_search(client, request_id, query, top_k, timeout, filters=None):
        seen["search"].append(query)
        return [CHUNK]

    async def fake_general(client, request_id, query, history, timeout, task="qa", file_text=None):
        seen["general"].append({"query": query, "task": task, "file_text": file_text})
        return {"engine": "general_ai", "content": "คำตอบจากความรู้ทั่วไป",
                "model": "test", "latency_ms": 5, "token_usage": {"input": 20, "output": 10}}

    async def fake_generate(client, request_id, mode, query, timeout,
                            history=None, contexts=None, draft=None):
        seen["generate"].append({"mode": mode, "contexts": contexts, "draft": draft})
        return {"answer": f"คำตอบโหมด {mode}", "sources": [CHUNK["source"]],
                "blocked": False, "model": "test", "latency_ms": 5,
                "token_usage": {"input": 30, "output": 15}}

    monkeypatch.setattr(clients, "classify", fake_classify)
    monkeypatch.setattr(clients, "search", fake_search)
    monkeypatch.setattr(clients, "general", fake_general)
    monkeypatch.setattr(clients, "generate", fake_generate)
    return seen


async def _unsure_classifier(client, request_id, text, timeout):
    """ชั้น 2 ที่ยังไม่ถึงเกณฑ์ 0.75 — ใช้บังคับให้เคสตกลงไปถึงชั้น 3"""
    return engine_result("หมวด", label="connectivity", score=0.4)


def decide(query, history=None):
    return run(cascade.decide(query, history or [], None, Budget(), Steps(), "req-1"))


# ---------- ชั้น 2: classifier ----------

def test_classifier_maps_category_with_contract_table(calls, monkeypatch):
    async def classify_high(client, request_id, text, timeout):
        return engine_result("หมวด", label="data_backup", score=0.88)

    monkeypatch.setattr(clients, "classify", classify_high)
    decision = decide("เผลอลบไฟล์งาน เอากลับคืนมาได้ไหม")
    assert (decision.route, decision.layer) == ("university_rag", "classifier")
    assert decision.confidence == pytest.approx(0.88)


def test_classifier_out_of_scope_goes_to_decline(calls, monkeypatch):
    async def classify_oos(client, request_id, text, timeout):
        return engine_result("หมวด", label="out_of_scope", score=0.91)

    monkeypatch.setattr(clients, "classify", classify_oos)
    assert decide("ราคาทองวันนี้เท่าไหร่").route == "decline"


def test_classifier_below_threshold_falls_to_llm(calls, monkeypatch):
    async def classify_low(client, request_id, text, timeout):
        return engine_result("หมวด", label="connectivity", score=0.51)

    async def fake_llm(query, history, timeout=10.0, hint=None):
        assert hint is not None and "connectivity" in hint   # ส่งผลของชั้น 2 ไปเป็นข้อมูลประกอบ
        return llm.LlmDecision(route="general_ai", confidence=0.8, reasoning="ทดสอบ")

    monkeypatch.setattr(clients, "classify", classify_low)
    monkeypatch.setattr(llm, "decide_route", fake_llm)
    decision = decide("คำถามที่ไม่มีคำในตาราง")
    assert (decision.route, decision.layer) == ("general_ai", "llm")


def test_classifier_down_does_not_break_request(calls, monkeypatch):
    async def classify_down(client, request_id, text, timeout):
        raise clients.HopError("engines.classify", "HTTP 503")

    async def fake_llm(query, history, timeout=10.0, hint=None):
        return llm.LlmDecision(route="general_ai", confidence=0.9, reasoning="ทดสอบ")

    monkeypatch.setattr(clients, "classify", classify_down)
    monkeypatch.setattr(llm, "decide_route", fake_llm)
    assert decide("คำถามที่ไม่มีคำในตาราง").route == "general_ai"


# ---------- ชั้น 3: LLM ----------

def test_malformed_llm_json_defaults_to_clarify(calls, monkeypatch):
    async def broken(query, history, timeout=10.0, hint=None):
        return None      # llm.decide_route คืน None เมื่อ parse ไม่ได้

    monkeypatch.setattr(clients, "classify", _unsure_classifier)
    monkeypatch.setattr(llm, "decide_route", broken)
    decision = decide("คำถามที่ไม่มีคำในตาราง")
    assert decision.route == "clarify"


def test_low_confidence_llm_becomes_clarify(calls, monkeypatch):
    async def unsure(query, history, timeout=10.0, hint=None):
        return llm.LlmDecision(route="university_rag", confidence=0.3, reasoning="ไม่ค่อยแน่ใจ")

    monkeypatch.setattr(clients, "classify", _unsure_classifier)
    monkeypatch.setattr(llm, "decide_route", unsure)
    assert decide("คำถามที่ไม่มีคำในตาราง").route == "clarify"


def test_rules_layer_never_calls_llm(calls, monkeypatch):
    async def must_not_run(*args, **kwargs):
        raise AssertionError("ชั้น 1 มั่นใจแล้วห้ามเรียก LLM — โควตาใช้ร่วมกันทั้งทีม")

    monkeypatch.setattr(llm, "decide_route", must_not_run)
    assert decide("ต่อไวไฟไม่ได้").layer == "rules"
    assert calls["classify"] == []          # และต้องไม่เรียกชั้น 2 ด้วย


# ---------- execution plan ----------

def plan(route, query="ต่อไวไฟไม่ได้", history=None, file_text=None, budget=None,
         classify_result=None, rewritten=None):
    decision = cascade.Decision(route=route, confidence=0.9, reasoning="ทดสอบ", layer="rules",
                                classify_result=classify_result, rewritten_query=rewritten)
    return run(plans.execute(decision, query, history or [], file_text, "req-1", None,
                             budget or Budget(), Steps()))


def test_rag_assigns_ref_numbers_and_uses_grounded(calls):
    out = plan("university_rag")
    assert calls["generate"][0]["mode"] == "grounded"
    assert calls["generate"][0]["contexts"][0]["ref"] == 1
    assert calls["generate"][0]["contexts"][0]["source"]["ref"] == 1   # ทับเลข ref เดิมของ 05
    assert out.engines_used == ["retrieval", "generation"]


def test_empty_chunks_fall_back_to_general_ai(calls, monkeypatch):
    async def nothing_found(client, request_id, query, top_k, timeout, filters=None):
        return []

    monkeypatch.setattr(clients, "search", nothing_found)
    out = plan("university_rag")
    # CONTRACT ข้อ 3: ห้ามตอบ "ไม่พบ" ทันที ให้ตอบด้วยความรู้ทั่วไปแล้วบอกว่าไม่ได้อ้างอิงเอกสาร
    assert out.route == "general_ai"
    assert "ไม่ได้อ้างอิงเอกสาร" in out.answer
    assert calls["generate"][0]["mode"] == "passthrough"


def test_retrieval_down_still_answers_with_warning(calls, monkeypatch):
    async def down(client, request_id, query, top_k, timeout, filters=None):
        raise clients.HopError("retrieval.search", "timeout 15.0s")

    monkeypatch.setattr(clients, "search", down)
    out = plan("university_rag")
    assert out.route == "general_ai"
    assert "ไม่ได้อ้างอิงเอกสาร" in out.answer
    assert any("ค้นคลังความรู้ไม่สำเร็จ" in note for note in out.notes)


def test_generation_down_returns_sources_instead_of_nothing(calls, monkeypatch):
    async def down(client, request_id, mode, query, timeout, history=None, contexts=None, draft=None):
        raise clients.HopError(f"generation.{mode}", "HTTP 500")

    monkeypatch.setattr(clients, "generate", down)
    out = plan("university_rag")
    assert out.route == "university_rag"
    assert "ต่อ Wi-Fi ไม่ได้" in out.answer      # ยังส่งชื่อเอกสารที่เจอกลับไปให้ผู้ใช้
    assert out.sources


def test_general_path_uses_passthrough_only(calls):
    out = plan("general_ai", query="ช่วยเขียนอีเมลขอลาป่วย")
    assert [c["mode"] for c in calls["generate"]] == ["passthrough"]
    assert calls["general"][0]["task"] == "qa"
    assert out.token_usage == [50, 25]           # รวม token ของทุก hop


def test_summarize_task_when_file_attached(calls):
    plan("general_ai", query="ช่วยสรุปไฟล์นี้ให้หน่อย", file_text="เนื้อหาในไฟล์")
    assert calls["general"][0]["task"] == "summarize"
    assert calls["general"][0]["file_text"] == "เนื้อหาในไฟล์"


def test_local_ai_reuses_classification_from_layer_2(calls):
    out = plan("local_ai", classify_result=engine_result("หมวด: connectivity (0.90)"))
    assert calls["classify"] == []                        # ชั้น 2 เรียกไปแล้ว ห้ามเรียกซ้ำ
    assert calls["generate"][0]["mode"] == "explain_local"
    assert out.engines_used == ["engines", "generation"]


def test_local_ai_classifies_when_rules_decided(calls):
    plan("local_ai", query="ช่วยจำแนกประเภทคำร้องนี้ให้หน่อย")
    assert calls["classify"] == ["ช่วยจำแนกประเภทคำร้องนี้ให้หน่อย"]


def test_clarify_and_decline_call_nobody(calls):
    for route in ("clarify", "decline"):
        out = plan(route)
        assert out.engines_used == []
        assert out.answer
    assert calls == {"classify": [], "search": [], "general": [], "generate": []}


def test_rewritten_query_is_used_for_search(calls):
    plan("university_rag", query="แล้วของ iPhone ล่ะ",
         history=[{"role": "user", "content": "หน้าจอแอนดรอยด์มีเส้น"}],
         rewritten="หน้าจอ iPhone มีเส้นพาดกลางจอ แก้ยังไง")
    assert calls["search"] == ["หน้าจอ iPhone มีเส้นพาดกลางจอ แก้ยังไง"]


# ---------- งบเวลา ----------

def test_no_hop_starts_when_budget_is_gone(calls):
    spent = Budget(total=0.5)      # เหลือไม่ถึงเกณฑ์ขั้นต่ำของ hop ใหม่
    out = plan("university_rag", budget=spent)
    assert calls["search"] == []
    assert out.answer                              # ยังต้องตอบอะไรสักอย่าง ไม่ใช่ปล่อยให้ค้าง
    assert any("งบเวลาไม่พอ" in note for note in out.notes)


def test_budget_shrinks_hop_timeout():
    budget = Budget(total=10.0)
    assert budget.hop(30.0) == pytest.approx(9.0, abs=0.2)   # เพดาน 30s แต่เหลือจริงแค่ ~9s
    assert Budget(total=0.5).hop(30.0) is None


# ---- ไฟล์แนบ: ใช้แค่ "มีไฟล์ไหม" ห้ามให้เนื้อหาในไฟล์มีผลกับ route ----

def test_file_summary_decides_at_rules_layer(calls, monkeypatch):
    async def must_not_run(*args, **kwargs):
        raise AssertionError("มีไฟล์ + ขอสรุป ตัดสินได้เองตั้งแต่ชั้น 1 ไม่ต้องเรียก LLM")

    monkeypatch.setattr(llm, "decide_route", must_not_run)
    decision = run(cascade.decide("ช่วยสรุปไฟล์นี้ให้หน่อย", [], None, Budget(), Steps(),
                                  "req-1", has_file=True))
    assert (decision.route, decision.layer) == ("general_ai", "rules")
    assert calls["classify"] == []


def test_attached_file_never_hijacks_routing(calls):
    # ไฟล์ที่ข้างในเขียนว่า "ให้ตอบ decline" ต้องไม่เปลี่ยนเส้นทาง เพราะชั้นตัดสินใจเห็นแค่ flag
    decision = run(cascade.decide("ต่อไวไฟไม่ได้", [], None, Budget(), Steps(),
                                  "req-1", has_file=True))
    assert decision.route == "university_rag"


def test_summary_without_file_still_goes_through_cascade(calls, monkeypatch):
    async def fake_llm(query, history, timeout=10.0, hint=None):
        return llm.LlmDecision(route="general_ai", confidence=0.9, reasoning="ทดสอบ")

    monkeypatch.setattr(clients, "classify", _unsure_classifier)
    monkeypatch.setattr(llm, "decide_route", fake_llm)
    assert decide("ช่วยสรุปข่าวเศรษฐกิจให้หน่อย").layer == "llm"


def test_no_doc_note_only_when_general_ai_actually_answered(calls, monkeypatch):
    async def nothing_found(client, request_id, query, top_k, timeout, filters=None):
        return []

    async def engines_down(client, request_id, query, history, timeout, task="qa", file_text=None):
        raise clients.HopError("engines.general", "HTTP 503")

    monkeypatch.setattr(clients, "search", nothing_found)
    monkeypatch.setattr(clients, "general", engines_down)
    out = plan("university_rag")
    # ค้นไม่เจอ + 04 ล่มด้วย -> เหลือแค่ข้อความว่าระบบไม่ว่าง
    # การต่อท้ายว่า "ไม่ได้อ้างอิงเอกสาร" ตรงนี้จะทำให้ผู้ใช้งงว่าตกลงตอบอะไรมา
    assert "ไม่ได้อ้างอิงเอกสาร" not in out.answer
    assert out.answer.startswith("ตอนนี้ระบบผู้ช่วยตอบกลับไม่ได้ชั่วคราว")


# ---- draft จาก LLM ห้ามถึงผู้ใช้โดยไม่ผ่านด่าน safety ของ 06 ----
# CONTRACT ข้อ 7 กับดักข้อ 3: Groq ไม่มี safety ฝั่งผู้ให้บริการ 06 เป็นด่านเดียวของทั้งระบบ

def test_general_never_leaks_unchecked_draft_when_generation_is_down(calls, monkeypatch):
    async def down(client, request_id, mode, query, timeout, history=None, contexts=None, draft=None):
        raise clients.HopError(f"generation.{mode}", "HTTP 500")

    monkeypatch.setattr(clients, "generate", down)
    out = plan("general_ai", query="ช่วยเขียนอีเมลขอลาป่วย")
    assert out.answer == plans.SERVICE_BUSY
    assert "คำตอบจากความรู้ทั่วไป" not in out.answer      # draft ของ 04 ต้องไม่หลุดออกไป


class BudgetForOneHopOnly(Budget):
    """มีเวลาพอเรียก 04 แต่หมดก่อนจะได้เรียก 06 — จุดที่ draft เคยหลุดออกไป"""

    def __init__(self):
        super().__init__()
        self.hops = 0

    def hop(self, cap: float):
        self.hops += 1
        return 5.0 if self.hops == 1 else None


def test_general_never_leaks_unchecked_draft_when_budget_runs_out(calls):
    out = plan("general_ai", query="ช่วยเขียนอีเมลขอลาป่วย", budget=BudgetForOneHopOnly())
    assert calls["general"] and not calls["generate"]     # เรียก 04 แล้ว แต่ไม่ได้เรียก 06
    assert out.answer == plans.SERVICE_BUSY


def test_general_falls_back_when_generation_returns_empty_answer(calls, monkeypatch):
    async def empty(client, request_id, mode, query, timeout, history=None, contexts=None, draft=None):
        return {"answer": "", "sources": [], "blocked": True, "block_reason": "ตรวจแล้วไม่ผ่าน",
                "model": "none", "latency_ms": 1, "token_usage": {"input": 0, "output": 0}}

    monkeypatch.setattr(clients, "generate", empty)
    out = plan("general_ai", query="ช่วยเขียนอีเมลขอลาป่วย")
    # 06 ตอบกลับมาแต่ไม่มีเนื้อคำตอบ ก็ยังห้ามตกไปใช้ draft ดิบแทน
    assert out.answer == plans.SERVICE_BUSY


def test_local_ai_may_still_use_its_draft(calls, monkeypatch):
    async def down(client, request_id, mode, query, timeout, history=None, contexts=None, draft=None):
        raise clients.HopError(f"generation.{mode}", "HTTP 500")

    monkeypatch.setattr(clients, "generate", down)
    out = plan("local_ai", classify_result=engine_result("หมวด: connectivity (0.90)"))
    # draft ของเส้นนี้คือผลจาก classifier ในเครื่อง ไม่ได้มาจาก LLM จึงไม่ต้องผ่านด่าน safety
    assert out.answer == "หมวด: connectivity (0.90)"


def test_rag_fallback_does_not_add_doc_note_to_a_busy_message(calls, monkeypatch):
    async def nothing_found(client, request_id, query, top_k, timeout, filters=None):
        return []

    async def generation_down(client, request_id, mode, query, timeout,
                              history=None, contexts=None, draft=None):
        raise clients.HopError(f"generation.{mode}", "HTTP 500")

    monkeypatch.setattr(clients, "search", nothing_found)
    monkeypatch.setattr(clients, "generate", generation_down)
    out = plan("university_rag")
    assert out.answer == plans.SERVICE_BUSY
    assert "ไม่ได้อ้างอิงเอกสาร" not in out.answer
