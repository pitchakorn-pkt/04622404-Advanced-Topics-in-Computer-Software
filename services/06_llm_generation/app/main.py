"""06 LLM Generation — ด่านสุดท้ายก่อนถึงผู้ใช้

สามโหมดคือสามงานคนละแบบ แยกฟังก์ชันชัดเจน
  grounded       เรียก LLM เขียนคำตอบจาก contexts พร้อม [n] ที่ตรวจสอบได้
  passthrough    ไม่เรียก LLM ทำแค่ safety + จัด markdown ของ draft แล้วคืน model="none"
  explain_local  เรียก LLM สั้น ๆ แปลงผล classifier เป็นประโยคคน
"""
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import jinja2
from fastapi import FastAPI
from openai import AsyncOpenAI

from .common import health_payload, jlog, request_id_middleware  # noqa: F401
from .schemas import GenerateRequest, GenerateResponse, Source, TokenUsage

app = FastAPI(title="chuayduay · generation")
app.middleware("http")(request_id_middleware)

# ------------------------------------------------------------------------------
# Configuration & Setup
# ------------------------------------------------------------------------------
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(PROMPTS_DIR),
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)

# PII Regex Patterns for Thai Data
REGEX_THAI_NATIONAL_ID = re.compile(r"\b[1-9]\d{12}\b")
REGEX_PHONE_NUMBER = re.compile(r"\b0[689]\d{8}\b|\b0[23457]\d{7}\b")
REGEX_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def get_llm_client() -> Tuple[AsyncOpenAI, str]:
    """ดึง OpenAI Client ที่ชี้ไปยัง Groq (หรือ Fallback) ตาม CONTRACT §7"""
    primary_provider = os.getenv("LLM_PRIMARY", "groq").lower()

    if primary_provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
        base_url = "https://api.groq.com/openai/v1"
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    elif primary_provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "")
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        model = os.getenv("GEMINI_MODEL", "")
    else:
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = "https://api.openai.com/v1"
        model = os.getenv("OPENAI_MODEL", "")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return client, model


def mask_pii(text: str) -> str:
    """Mask ข้อมูลส่วนบุคคล (PII) ด้วย Regex"""
    text = REGEX_THAI_NATIONAL_ID.sub("[MASKED_NATIONAL_ID]", text)
    text = REGEX_PHONE_NUMBER.sub("[MASKED_PHONE]", text)
    text = REGEX_EMAIL.sub("[MASKED_EMAIL]", text)
    return text


def verify_and_clean_citations(
    answer: str, available_contexts: List[Any]
) -> Tuple[str, List[Source]]:
    """ดึง [n] ทั้งหมดจากคำตอบ -> ลบเลขที่ไม่มีใน contexts -> คืน sources เฉพาะที่ถูกอ้างจริง"""
    valid_refs = {ctx.ref: ctx.source for ctx in available_contexts if ctx.ref is not None}
    found_refs = set()

    def replace_citation(match: re.Match) -> str:
        ref_num = int(match.group(1))
        if ref_num in valid_refs:
            found_refs.add(ref_num)
            return f"[{ref_num}]"
        # หากอ้างอิงเลขที่ไม่มีจริง ตัดออกจากคำตอบ
        return ""

    # ตรวจจับ pattern [1], [2]
    cleaned_answer = re.sub(r"\[(\d+)\]", replace_citation, answer)
    # ทำความสะอาดช่องว่างส่วนเกินที่เกิดจากการตัด citation
    cleaned_answer = re.sub(r" +", " ", cleaned_answer)

    ordered_sources = [valid_refs[ref_num] for ref_num in sorted(found_refs)]
    return cleaned_answer.strip(), ordered_sources


# ------------------------------------------------------------------------------
# Endpoints & Logic Handlers
# ------------------------------------------------------------------------------
@app.get("/health")
async def health():
    return health_payload()


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    jlog(event="generate", mode=req.mode, contexts=len(req.contexts))

    if req.mode == "passthrough":
        return await handle_passthrough(req)

    if req.mode == "explain_local":
        return await handle_explain_local(req)

    if req.mode == "grounded":
        return await handle_grounded(req)

    # Fallback เผื่อ mode ไม่ตรง
    return GenerateResponse(
        request_id=req.request_id,
        answer="ข้อผิดพลาด: ไม่รองรับโหมดการทำงานที่ระบุ",
        sources=[],
        blocked=True,
        block_reason="Invalid mode",
        model="none",
        latency_ms=1,
        token_usage=TokenUsage(),
    )


async def handle_passthrough(req: GenerateRequest) -> GenerateResponse:
    """mode passthrough: ไม่เรียก LLM ทำแค่ safety + จัด markdown ของ draft"""
    draft = req.draft or ""
    safe_draft = mask_pii(draft)

    return GenerateResponse(
        request_id=req.request_id,
        answer=safe_draft.strip(),
        sources=[],
        blocked=False,
        block_reason=None,
        model="none",
        latency_ms=1,
        token_usage=TokenUsage(),
    )


async def handle_explain_local(req: GenerateRequest) -> GenerateResponse:
    """mode explain_local: เรียก LLM สั้น ๆ แปลงผล classifier เป็นประโยคคน"""
    client, model_name = get_llm_client()
    temperature = float(os.getenv("GENERATION_TEMPERATURE", "0.3"))
    max_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "256"))

    prompt = (
        "คุณคือระบบผู้ช่วยตอบปัญหาไอที 'ช่วยด้วย'\n"
        "โปรดนำผลการจำแนกประเภทคำถาม (Classification Result) ต่อไปนี้ "
        "มาอธิบายให้ผู้ใช้ฟังด้วยภาษาที่สุภาพ เข้าใจง่าย และสั้นกระชับ (ไม่เกิน 2 ประโยค) "
        "พร้อมแนะนำขั้นตอนถัดไปเบื้องต้น:\n\n"
        f"ผลลัพธ์: {req.draft or 'ไม่ทราบประเภท'}"
    )

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            return GenerateResponse(
                request_id=req.request_id,
                answer="คำขอถูกระงับเนื่องจากติดเงื่อนไขความปลอดภัย",
                sources=[],
                blocked=True,
                block_reason="content_filter",
                model=model_name,
                latency_ms=1,
                token_usage=TokenUsage(),
            )

        raw_answer = choice.message.content or ""
        safe_answer = mask_pii(raw_answer)

        usage = TokenUsage()
        if response.usage:
            usage = TokenUsage(
                input=response.usage.prompt_tokens,
                output=response.usage.completion_tokens,
            )

        return GenerateResponse(
            request_id=req.request_id,
            answer=safe_answer.strip(),
            sources=[],
            blocked=False,
            block_reason=None,
            model=model_name,
            latency_ms=1,
            token_usage=usage,
        )
    except Exception as e:
        jlog(event="llm_error", mode="explain_local", error=str(e))
        # Fallback ตอบแบบไม่พึ่ง LLM หากมีข้อผิดพลาด
        return GenerateResponse(
            request_id=req.request_id,
            answer=mask_pii(req.draft or "ระบบได้ทำการจำแนกประเภทคำร้องของคุณแล้ว"),
            sources=[],
            blocked=False,
            block_reason=None,
            model="fallback-none",
            latency_ms=1,
            token_usage=TokenUsage(),
        )


async def handle_grounded(req: GenerateRequest) -> GenerateResponse:
    """mode grounded: เรียก LLM เขียนคำตอบจาก contexts พร้อม [n] ที่ตรวจสอบได้จริง"""
    # กรณี Contexts ว่างเปล่า
    if not req.contexts:
        return GenerateResponse(
            request_id=req.request_id,
            answer="ขออภัย ไม่พบข้อมูลที่เพียงพอในคลังความรู้สำหรับตอบคำถามนี้",
            sources=[],
            blocked=False,
            block_reason=None,
            model="none",
            latency_ms=1,
            token_usage=TokenUsage(),
        )

    client, model_name = get_llm_client()
    temperature = float(os.getenv("GENERATION_TEMPERATURE", "0.3"))
    max_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "1024"))

    # Render Prompt Template จาก grounded.j2
    template = jinja_env.get_template("grounded.j2")
    rendered_prompt = template.render(
        contexts=req.contexts,
        history=req.history,
        query=req.query,
    )

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": rendered_prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            return GenerateResponse(
                request_id=req.request_id,
                answer="เนื้อหาถูกระงับเนื่องจากเงื่อนไขความปลอดภัยของระบบ",
                sources=[],
                blocked=True,
                block_reason="content_filter",
                model=model_name,
                latency_ms=1,
                token_usage=TokenUsage(),
            )

        raw_answer = choice.message.content or ""

        # Citation Verification: ตรวจสอบและคัดกรองเลขอ้างอิง [n] ที่ไม่มีอยู่จริงออก
        cleaned_answer, cited_sources = verify_and_clean_citations(raw_answer, req.contexts)

        # Mask PII
        final_answer = mask_pii(cleaned_answer)

        usage = TokenUsage()
        if response.usage:
            usage = TokenUsage(
                input=response.usage.prompt_tokens,
                output=response.usage.completion_tokens,
            )

        return GenerateResponse(
            request_id=req.request_id,
            answer=final_answer.strip(),
            sources=cited_sources,
            blocked=False,
            block_reason=None,
            model=model_name,
            latency_ms=1,
            token_usage=usage,
        )
    except Exception as e:
        jlog(event="llm_error", mode="grounded", error=str(e))
        return GenerateResponse(
            request_id=req.request_id,
            answer="เกิดข้อผิดพลาดในการเชื่อมต่อกับระบบประมวลผลภาษา กรุณาลองใหม่อีกครั้ง",
            sources=[],
            blocked=True,
            block_reason=str(e),
            model="error",
            latency_ms=1,
            token_usage=TokenUsage(),
        )

    # grounded — ของจริงต้องตรวจ [n] ทุกตัวว่ามีอยู่ใน contexts จริง ตัวที่ไม่มีให้ตัดทิ้ง
    cited = [c.source for c in req.contexts[:2]]
    marks = " ".join(f"[{c.ref}]" for c in req.contexts[:2])
    return GenerateResponse(
        request_id=req.request_id,
        answer=f"(ตัวอย่างจาก stub) ตอบจากเอกสารที่ค้นเจอ {marks}".strip(),
        sources=cited, model="stub", latency_ms=1, token_usage=TokenUsage(),
    )
