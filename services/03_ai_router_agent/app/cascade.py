"""Cascade router — ตัดสินใจเป็นชั้น หยุดทันทีที่ชั้นไหนมั่นใจพอ

  ชั้น 0 guard      ข้อความว่าง/สั้นเกิน/อ้างอิงลอย ๆ -> clarify · คำขอที่ไม่ควรตอบ -> decline
  ชั้น 1 rules      ตาราง keyword ที่ล็อกแล้ว -> university_rag / local_ai (confidence 0.9)
  ชั้น 2 classifier เรียก 04 /local/classify ถ้า score >= 0.75 แปลงหมวดเป็น route ตาม CONTRACT ข้อ 3
  ชั้น 3 llm        ที่เหลือค่อยถาม LLM เป็น JSON · confidence < 0.5 -> clarify

เหตุผลที่ต้องทำเป็นชั้น ไม่ใช่ถาม LLM ทุกครั้ง: เร็วกว่ามากและไม่กินโควตาที่ทั้งทีมแชร์กัน
ทุก request บันทึกว่าจบที่ชั้นไหนใน `decided_at_layer` — ตัวเลขนี้เก็บย้อนหลังไม่ได้ถ้าลืมใส่
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from . import clients, guard, llm, rules
from .budget import Budget, Steps
from .common import jlog
from .config import (CATEGORY_ROUTE, CLASSIFIER_THRESHOLD, LLM_MIN_CONFIDENCE,
                     SUMMARIZE_CUES, T_ENGINES, T_LLM)


@dataclass
class Decision:
    route: str
    confidence: float
    reasoning: str
    layer: str
    category: str | None = None
    rewritten_query: str | None = None
    # ผลจากชั้น 2 เก็บไว้ให้ execution plan ใช้ซ้ำ จะได้ไม่ต้องเรียก 04 สองรอบ
    classify_result: dict | None = None
    token_usage: list[int] = field(default_factory=lambda: [0, 0])


def _add_tokens(decision_tokens: list[int], pair: tuple[int, int]) -> None:
    decision_tokens[0] += pair[0]
    decision_tokens[1] += pair[1]


async def decide(query: str, history: list[dict], client: httpx.AsyncClient,
                 budget: Budget, steps: Steps, request_id: str,
                 has_file: bool = False) -> Decision:
    """has_file บอกแค่ว่า "มีไฟล์แนบมาไหม" เท่านั้น — เนื้อหาในไฟล์ไม่เคยเข้ามาถึงชั้นตัดสินใจ
    ไม่งั้นใครก็แนบไฟล์ที่เขียนว่า "ให้ตอบ decline" แล้วสั่งการ router ได้ (prompt injection)
    """
    tokens = [0, 0]

    # ---- ชั้น 0: guard ----
    with steps.step("router.guard"):
        hit = guard.check(query, history_len=len(history))
    if hit:
        return Decision(route=hit.route, confidence=hit.confidence,
                        reasoning=hit.reasoning, layer="guard", token_usage=tokens)

    # ---- ชั้น 1: rules ----
    # แนบไฟล์มาแล้วขอให้สรุป = general_ai task=summarize ตัดสินได้เลยไม่ต้องเรียก LLM
    if has_file and any(cue in query.lower() for cue in SUMMARIZE_CUES):
        return Decision(route="general_ai", confidence=0.9, layer="rules",
                        reasoning="ชั้น rules: ผู้ใช้ขอให้สรุปไฟล์ที่แนบมา", token_usage=tokens)

    with steps.step("router.rules"):
        rule = rules.match(query)
    if rule:
        return Decision(route=rule.route, confidence=rule.confidence, reasoning=rule.reasoning,
                        layer="rules", category=rule.category, token_usage=tokens)

    # ---- ชั้น 2: classifier ของโมดูล 04 ----
    hint = None
    classify_result = None
    timeout = budget.hop(T_ENGINES)
    if timeout is None:
        jlog(event="layer_skipped", layer="classifier", reason="งบเวลาไม่พอ")
    else:
        try:
            with steps.step("engines.classify"):
                classify_result = await clients.classify(client, request_id, query, timeout)
        except clients.HopError as exc:
            # 04 ล่มหรือยังโหลดโมเดลไม่เสร็จ ไม่ใช่เหตุให้ request พัง — ตกไปชั้น 3 ต่อ
            jlog(event="layer_failed", layer="classifier", reason=exc.reason)
        else:
            data = classify_result.get("data") or {}
            label, score = data.get("label"), float(data.get("score") or 0.0)
            hint = f"{label} ({score:.2f})"
            if label in CATEGORY_ROUTE and score >= CLASSIFIER_THRESHOLD:
                # ตาราง map อยู่ใน CONTRACT ข้อ 3 ล็อกแล้ว ห้ามตีความเอง
                return Decision(route=CATEGORY_ROUTE[label], confidence=score,
                                reasoning=f"ชั้น classifier: โมเดลจำแนกได้หมวด {label} "
                                          f"ที่ความมั่นใจ {score:.2f} (เกณฑ์ {CLASSIFIER_THRESHOLD})",
                                layer="classifier", category=label,
                                classify_result=classify_result, token_usage=tokens)
            jlog(event="classifier_below_threshold", label=label, score=round(score, 4))

    # ---- ชั้น 3: LLM ----
    timeout = budget.hop(T_LLM)
    if timeout is None:
        return Decision(route="clarify", confidence=0.3,
                        reasoning="งบเวลาเหลือไม่พอจะถาม LLM จึงขอข้อมูลเพิ่มแทนการเดา",
                        layer="llm", classify_result=classify_result, token_usage=tokens)

    with steps.step("router.llm"):
        verdict = await llm.decide_route(query, history, timeout=timeout, hint=hint)

    if verdict is None:
        # เรียกไม่ได้ หรือ JSON เพี้ยน — ค่า default คือถามกลับ ห้ามเดา route
        return Decision(route="clarify", confidence=0.3,
                        reasoning="ชั้น llm ตอบกลับไม่ได้หรือรูปแบบไม่ถูกต้อง จึงขอข้อมูลเพิ่มแทน",
                        layer="llm", classify_result=classify_result, token_usage=tokens)

    _add_tokens(tokens, verdict.token_usage)

    if verdict.confidence < LLM_MIN_CONFIDENCE:
        return Decision(route="clarify", confidence=verdict.confidence,
                        reasoning=f"ชั้น llm มั่นใจแค่ {verdict.confidence:.2f} "
                                  f"({verdict.reasoning}) จึงขอข้อมูลเพิ่ม",
                        layer="llm", classify_result=classify_result, token_usage=tokens)

    return Decision(route=verdict.route, confidence=verdict.confidence,
                    reasoning=f"ชั้น llm: {verdict.reasoning}", layer="llm",
                    rewritten_query=verdict.rewritten_query,
                    classify_result=classify_result, token_usage=tokens)
