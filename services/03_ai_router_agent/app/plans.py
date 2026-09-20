"""Execution plan ของแต่ละ route — ตัดสินใจเสร็จแล้วต้องไปเรียกใครต่อ

  university_rag  (rewrite ถ้าเป็น follow-up) -> 05 /search -> 06 /generate mode=grounded
  general_ai      04 /general -> 06 /generate mode=passthrough   (passthrough ไม่เรียก LLM ซ้ำ)
  local_ai        04 /local/classify -> 06 /generate mode=explain_local
  clarify         ตอบคำถามกลับ 1 ข้อจาก template ไม่เรียกใคร
  decline         ปฏิเสธอย่างสุภาพ + ช่องทางติดต่อคน ไม่เรียกใคร

ทุกเส้นมี fallback เสมอ เพราะ "ตอบได้ไม่ครบ" ดีกว่า "ตอบไม่ได้เลย"
และทุกครั้งที่คำตอบไม่ได้อ้างอิงเอกสาร ต้องบอกผู้ใช้ตรง ๆ ห้ามปล่อยให้เข้าใจผิดว่ามีเอกสารรองรับ
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from . import clients, guard, llm
from .budget import Budget, Steps
from .cascade import Decision
from .common import jlog
from .config import SUMMARIZE_CUES, T_ENGINES, T_GENERATION, T_LLM, T_RETRIEVAL, TOP_K

CLARIFY_TEMPLATE = (
    "ขอรายละเอียดเพิ่มอีกนิดครับ ช่วยเล่าอาการที่เจอหน่อย "
    "ถ้าเป็นเรื่องอุปกรณ์บอกด้วยว่าใช้มือถือหรือคอมพิวเตอร์ครับ"
)

DECLINE_TEMPLATE = (
    "ขอโทษครับ เรื่องนี้ผมช่วยไม่ได้\n\n"
    "ถ้าเป็นปัญหาของบัญชีหรืออุปกรณ์ของคุณเอง เช่น ถูกเข้าถึงโดยไม่ได้รับอนุญาต "
    "แนะนำให้ติดต่อผู้ดูแลระบบของหน่วยงาน หรือศูนย์บริการของผู้ให้บริการโดยตรง "
    "และถ้าเกี่ยวข้องกับความเสียหายทางการเงิน สามารถแจ้งสายด่วนตำรวจไซเบอร์ 1441 ได้ครับ"
)

NO_DOC_NOTE = (
    "\n\n> หมายเหตุ: คำตอบนี้มาจากความรู้ทั่วไปของผู้ช่วย ไม่ได้อ้างอิงเอกสารในคลังความรู้"
)

SERVICE_BUSY = (
    "ตอนนี้ระบบผู้ช่วยตอบกลับไม่ได้ชั่วคราวครับ รบกวนลองใหม่อีกครั้งในอีกสักครู่ "
    "ถ้ายังไม่ได้แนะนำให้ติดต่อเจ้าหน้าที่ผู้ดูแลระบบโดยตรง"
)

# 06 ตอบประโยคนี้เมื่อเรียบเรียงจาก contexts ไม่ได้ — เกิดได้แม้ 05 จะคืน chunk มาแล้ว
# เช่น คำถามนอกคลัง (ปริ้นเตอร์) หรือคำถามภาษาอังกฤษ ถ้าจบแค่นี้ผู้ใช้ไม่ได้อะไรกลับไปเลย
NO_ANSWER_PREFIXES = ("ขออภัย ไม่พบข้อมูลที่เพียงพอ", "ไม่พบข้อมูลที่เพียงพอ")


@dataclass
class Outcome:
    answer: str
    route: str
    sources: list[dict] = field(default_factory=list)
    engines_used: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    token_usage: list[int] = field(default_factory=lambda: [0, 0])

    def add_tokens(self, payload: dict | None) -> None:
        usage = (payload or {}).get("token_usage") or {}
        self.token_usage[0] += int(usage.get("input") or 0)
        self.token_usage[1] += int(usage.get("output") or 0)

    def use(self, engine: str) -> None:
        if engine not in self.engines_used:
            self.engines_used.append(engine)


async def execute(decision: Decision, query: str, history: list[dict], file_text: str | None,
                  request_id: str, client: httpx.AsyncClient, budget: Budget,
                  steps: Steps) -> Outcome:
    if decision.route == "clarify":
        return Outcome(answer=CLARIFY_TEMPLATE, route="clarify")

    if decision.route == "decline":
        return Outcome(answer=DECLINE_TEMPLATE, route="decline")

    if decision.route == "university_rag":
        return await _rag(decision, query, history, file_text, request_id, client, budget, steps)

    if decision.route == "local_ai":
        return await _local(decision, query, request_id, client, budget, steps)

    return await _general(query, history, file_text, request_id, client, budget, steps)


async def _search_query(decision: Decision, query: str, history: list[dict],
                        budget: Budget, steps: Steps) -> tuple[str, list[int]]:
    """คำถาม follow-up ต้องเติมบริบทก่อนค้น ไม่งั้น 'แล้วของรุ่นเก่าล่ะ' จะค้นไม่เจออะไรเลย"""
    tokens = [0, 0]
    if decision.rewritten_query:
        return decision.rewritten_query, tokens          # ชั้น 3 เขียนมาให้แล้ว ไม่ต้องเรียกซ้ำ
    if not history or not guard.is_follow_up(query):
        return query, tokens

    timeout = budget.hop(T_LLM)
    if timeout is None:
        jlog(event="rewrite_skipped", reason="งบเวลาไม่พอ")
        return query, tokens

    with steps.step("router.rewrite"):
        rewritten, usage = await llm.rewrite_query(query, history, timeout=timeout)
    tokens[0] += usage[0]
    tokens[1] += usage[1]
    if rewritten:
        jlog(event="rewrite", original=query, rewritten=rewritten)
        return rewritten, tokens
    return query, tokens


async def _rag(decision: Decision, query: str, history: list[dict], file_text: str | None,
               request_id: str, client: httpx.AsyncClient, budget: Budget,
               steps: Steps) -> Outcome:
    out = Outcome(answer="", route="university_rag")

    search_query, rewrite_tokens = await _search_query(decision, query, history, budget, steps)
    out.token_usage[0] += rewrite_tokens[0]
    out.token_usage[1] += rewrite_tokens[1]
    if search_query != query:
        out.notes.append(f"เขียนคำถามใหม่ก่อนค้นเป็น: {search_query}")

    timeout = budget.hop(T_RETRIEVAL)
    chunks: list[dict] = []
    if timeout is None:
        out.notes.append("งบเวลาไม่พอสำหรับการค้นคลังความรู้")
    else:
        try:
            with steps.step("retrieval.search"):
                chunks = await clients.search(client, request_id, search_query, TOP_K, timeout)
            out.use("retrieval")
        except clients.HopError as exc:
            # 05 ล่ม -> ยังตอบได้ด้วยความรู้ทั่วไป แต่ต้องบอกผู้ใช้ว่าไม่ได้อ้างอิงเอกสาร
            jlog(event="retrieval_down", reason=exc.reason)
            out.notes.append(f"ค้นคลังความรู้ไม่สำเร็จ ({exc.reason}) จึงตอบจากความรู้ทั่วไปแทน")

    if not chunks:
        # CONTRACT ข้อ 3: chunks ว่าง -> fallback เป็น general_ai พร้อมบอกว่าไม่ได้อ้างอิงเอกสาร
        # ห้ามตอบ "ไม่พบ" ทันที เพราะคลังของเราไม่ได้ครอบคลุมทุกเรื่อง
        note = ("ค้นแล้วไม่เจอเอกสารที่เกี่ยวข้อง จึงตอบจากความรู้ทั่วไปแทน"
                if "ค้นคลังความรู้ไม่สำเร็จ" not in " ".join(out.notes) else "")
        return await _fall_back_to_general(out, note, query, history, file_text,
                                           request_id, client, budget, steps)

    # เลข ref เป็นหน้าที่ของ router — 06 เอาไปใช้ตรง ๆ จะได้ไม่มีเลขชนกัน
    contexts = [{"ref": i + 1, "text": c.get("text", ""),
                 "source": {**c.get("source", {}), "ref": i + 1}}
                for i, c in enumerate(chunks)]

    timeout = budget.hop(T_GENERATION)
    if timeout is None:
        out.answer = _sources_only_answer(contexts)
        out.sources = [c["source"] for c in contexts]
        out.notes.append("งบเวลาไม่พอสำหรับการเรียบเรียงคำตอบ จึงส่งเอกสารที่เกี่ยวข้องกลับไปก่อน")
        return out

    try:
        with steps.step("generation.grounded"):
            result = await clients.generate(client, request_id, "grounded", query, timeout,
                                            history=history, contexts=contexts)
    except clients.HopError as exc:
        jlog(event="generation_down", mode="grounded", reason=exc.reason)
        out.answer = _sources_only_answer(contexts)
        out.sources = [c["source"] for c in contexts]
        out.notes.append(f"เรียบเรียงคำตอบไม่สำเร็จ ({exc.reason}) จึงส่งเอกสารที่เกี่ยวข้องกลับไปก่อน")
        return out

    out.use("generation")
    out.add_tokens(result)
    answer = (result.get("answer") or "").strip()
    sources = result.get("sources") or []

    # 05 คืน chunk มาแล้วก็จริง แต่ 06 เรียบเรียงไม่ได้ (คำถามนอกคลัง หรือคนละภาษา)
    # ถ้าจบตรงนี้ผู้ใช้จะไม่ได้อะไรเลย ทั้งที่ยังตอบด้วยความรู้ทั่วไปได้ — ถอยเหมือนเคส chunks ว่าง
    # ดูช่วงต้นของคำตอบ ไม่ผูกกับตำแหน่งแรกเป๊ะ ๆ เพราะ LLM เติมคำนำหน้าได้ ("ขออภัยครับ ...")
    if not sources and any(p in answer[:120] for p in NO_ANSWER_PREFIXES):
        jlog(event="rag_dead_end", query_len=len(query), chunks=len(contexts))
        return await _fall_back_to_general(
            out, "เอกสารที่ค้นเจอไม่พอให้เรียบเรียงคำตอบ จึงตอบจากความรู้ทั่วไปแทน",
            query, history, file_text, request_id, client, budget, steps)

    out.answer = answer or _sources_only_answer(contexts)
    out.sources = sources
    if result.get("blocked"):
        out.notes.append(f"06 บล็อกคำตอบ: {result.get('block_reason')}")
    return out


async def _fall_back_to_general(out: Outcome, note: str, query: str, history: list[dict],
                                file_text: str | None, request_id: str,
                                client: httpx.AsyncClient, budget: Budget,
                                steps: Steps) -> Outcome:
    """เส้น rag ไปต่อไม่ได้ -> ตอบด้วยความรู้ทั่วไป แล้วบอกผู้ใช้ตรง ๆ ว่าไม่ได้อ้างอิงเอกสาร"""
    if note:
        out.notes.append(note)
    fallback = await _general(query, history, file_text, request_id, client, budget, steps)
    fallback.notes = out.notes + fallback.notes
    fallback.token_usage[0] += out.token_usage[0]
    fallback.token_usage[1] += out.token_usage[1]
    for engine in out.engines_used:
        fallback.use(engine)
    if "engines" in fallback.engines_used and fallback.answer != SERVICE_BUSY:
        # ต่อท้ายเฉพาะตอนที่ได้คำตอบจากความรู้ทั่วไปมาจริง ๆ
        # ถ้า 04 หรือ 06 ล่มด้วยจะเหลือแค่ข้อความว่าระบบไม่ว่าง การต่อท้ายตรงนั้นมีแต่ทำให้งง
        fallback.answer = fallback.answer.rstrip() + NO_DOC_NOTE
    return fallback


async def _general(query: str, history: list[dict], file_text: str | None, request_id: str,
                   client: httpx.AsyncClient, budget: Budget, steps: Steps) -> Outcome:
    out = Outcome(answer="", route="general_ai")

    task = "summarize" if (file_text and any(c in query.lower() for c in SUMMARIZE_CUES)) else "qa"

    timeout = budget.hop(T_ENGINES)
    if timeout is None:
        out.answer = SERVICE_BUSY
        out.notes.append("งบเวลาไม่พอสำหรับการเรียก general ai")
        return out

    try:
        with steps.step("engines.general"):
            engine = await clients.general(client, request_id, query, history, timeout,
                                           task=task, file_text=file_text)
    except clients.HopError as exc:
        jlog(event="engines_down", hop="general", reason=exc.reason)
        out.answer = SERVICE_BUSY
        out.notes.append(f"เรียก general ai ไม่สำเร็จ ({exc.reason})")
        return out

    out.use("engines")
    out.add_tokens(engine)
    draft = engine.get("content") or ""

    # passthrough ทำแค่ safety + จัดรูปแบบ ไม่เรียก LLM ซ้ำ — นี่คือเหตุผลทั้งหมดที่โหมดนี้มีอยู่
    timeout = budget.hop(T_GENERATION)
    if timeout is None:
        # ห้ามส่ง draft ดิบออกไปเด็ดขาด — Groq ไม่มี safety ฝั่งผู้ให้บริการ (CONTRACT ข้อ 7 กับดักข้อ 3)
        # 06 เป็นด่านเดียวที่กรอง PII และเนื้อหาอันตราย ข้ามด่านนี้เมื่อไหร่คือส่งของที่ยังไม่ตรวจถึงผู้ใช้
        out.answer = SERVICE_BUSY
        out.notes.append("งบเวลาไม่พอสำหรับขั้นตรวจความปลอดภัย จึงไม่ส่งคำตอบที่ยังไม่ผ่านการตรวจ")
        return out

    try:
        with steps.step("generation.passthrough"):
            result = await clients.generate(client, request_id, "passthrough", query, timeout,
                                            history=history, draft=draft)
    except clients.HopError as exc:
        jlog(event="generation_down", mode="passthrough", reason=exc.reason)
        out.answer = SERVICE_BUSY
        out.notes.append(f"ขั้นตรวจความปลอดภัยไม่ตอบ ({exc.reason}) จึงไม่ส่งคำตอบที่ยังไม่ผ่านการตรวจ")
        return out

    out.use("generation")
    out.add_tokens(result)
    out.answer = result.get("answer") or SERVICE_BUSY
    if result.get("blocked"):
        out.notes.append(f"06 บล็อกคำตอบ: {result.get('block_reason')}")
    return out


async def _local(decision: Decision, query: str, request_id: str, client: httpx.AsyncClient,
                 budget: Budget, steps: Steps) -> Outcome:
    out = Outcome(answer="", route="local_ai")

    result = decision.classify_result     # ชั้น 2 อาจเรียกไปแล้ว ไม่ต้องเรียกซ้ำให้เปลืองเวลา
    if result is None:
        timeout = budget.hop(T_ENGINES)
        if timeout is None:
            out.answer = SERVICE_BUSY
            out.notes.append("งบเวลาไม่พอสำหรับการจำแนกข้อความ")
            return out
        try:
            with steps.step("engines.classify"):
                result = await clients.classify(client, request_id, query, timeout)
        except clients.HopError as exc:
            jlog(event="engines_down", hop="classify", reason=exc.reason)
            out.answer = SERVICE_BUSY
            out.notes.append(f"เรียกโมเดลจำแนกไม่สำเร็จ ({exc.reason})")
            return out

    out.use("engines")
    out.add_tokens(result)
    draft = result.get("content") or ""

    timeout = budget.hop(T_GENERATION)
    if timeout is None:
        out.answer = draft or SERVICE_BUSY
        out.notes.append("งบเวลาไม่พอสำหรับการเรียบเรียงผลการจำแนก")
        return out

    try:
        with steps.step("generation.explain_local"):
            generated = await clients.generate(client, request_id, "explain_local", query,
                                               timeout, draft=draft)
    except clients.HopError as exc:
        jlog(event="generation_down", mode="explain_local", reason=exc.reason)
        out.answer = draft or SERVICE_BUSY
        out.notes.append(f"เรียบเรียงผลการจำแนกไม่สำเร็จ ({exc.reason})")
        return out

    out.use("generation")
    out.add_tokens(generated)
    out.answer = generated.get("answer") or draft
    if generated.get("blocked"):
        out.notes.append(f"06 บล็อกคำตอบ: {generated.get('block_reason')}")
    return out


def _sources_only_answer(contexts: list[dict]) -> str:
    """เมื่อเรียบเรียงคำตอบไม่ได้ ยังส่งเอกสารที่เจอกลับไปได้ ดีกว่าตอบว่าไม่มีอะไรเลย"""
    lines = ["ตอนนี้ยังเรียบเรียงคำตอบให้ไม่ได้ แต่เจอเอกสารที่น่าจะตรงกับคำถามครับ"]
    for ctx in contexts[:3]:
        title = (ctx.get("source") or {}).get("title") or "เอกสารในคลังความรู้"
        lines.append(f"- [{ctx['ref']}] {title}")
    return "\n".join(lines)
