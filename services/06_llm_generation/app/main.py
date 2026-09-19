"""06 LLM Generation — ด่านสุดท้ายก่อนถึงผู้ใช้

สามโหมดคือสามงานคนละแบบ แยกฟังก์ชันชัดเจน
    grounded        เรียก LLM เขียนคำตอบจาก contexts พร้อม [n] ที่ตรวจสอบได้
    passthrough     ไม่เรียก LLM ทำแค่ safety + จัด markdown ของ draft แล้วคืน model="none"
    explain_local   เรียก LLM สั้น ๆ แปลงผล classifier เป็นประโยคคน
"""
import os
import re
import time
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
REGEX_THAI_NATIONAL_ID = re.compile(r"(?<!\d)[1-9]\d{12}(?!\d)")
REGEX_PHONE_NUMBER = re.compile(r"(?<!\d)0[689](?:-?\d){8}(?!\d)|(?<!\d)0[23457](?:-?\d){7}(?!\d)")
REGEX_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def get_llm_client(provider: str) -> Tuple[AsyncOpenAI, str]:
    """ดึง OpenAI Client ตาม provider ที่ระบุ (รองรับ groq, gemini, openai)
    หากไม่มี API Key หรือตั้งค่าไม่ครบจะ raise ValueError เพื่อให้ข้ามไป Fallback ถัดไป
    """
    provider = provider.lower().strip()

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GROQ_API_KEY is empty")
        base_url = "https://api.groq.com/openai/v1"
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is empty")
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    else:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is empty")
        base_url = "https://api.openai.com/v1"
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=25.0)
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
    # ข้อ 1: แปลงวงเล็บอ้างอิงภาษาจีน/เอเชีย 【1】 ให้กลายเป็น [1] ก่อนทำการสแกน
    answer = re.sub(r"【\s*(\d+)\s*】", r"[\1]", answer)

    valid_refs = {ctx.ref: ctx.source for ctx in available_contexts if getattr(ctx, 'ref', None) is not None}
    found_refs = set()

    def replace_citation(match: re.Match) -> str:
        ref_num = int(match.group(1))
        if ref_num in valid_refs:
            found_refs.add(ref_num)
            return f"[{ref_num}]"
        return ""

    # ตรวจจับ pattern [1], [2]
    cleaned_answer = re.sub(r"\[(\d+)\]", replace_citation, answer)
    
    # รักษาระยะ Indent ของ Markdown list
    cleaned_answer = re.sub(r"(?<=\S) {2,}", " ", cleaned_answer)

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
    jlog(event="generate", mode=req.mode, contexts=len(req.contexts if req.contexts else []))

    if req.mode == "passthrough":
        return await handle_passthrough(req)

    if req.mode == "explain_local":
        return await handle_explain_local(req)

    if req.mode == "grounded":
        return await handle_grounded(req)

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
    start_time = time.perf_counter()
    draft = req.draft or ""
    safe_draft = mask_pii(draft)
    latency = int((time.perf_counter() - start_time) * 1000)

    return GenerateResponse(
        request_id=req.request_id,
        answer=safe_draft.strip(),
        sources=[],
        blocked=False,
        block_reason=None,
        model="none",
        latency_ms=latency,
        token_usage=TokenUsage(),
    )


async def handle_explain_local(req: GenerateRequest) -> GenerateResponse:
    """mode explain_local: เรียก LLM สั้น ๆ แปลงผล classifier เป็นประโยคคน พร้อมระบบ Fallback"""
    start_time = time.perf_counter()
    temperature = float(os.getenv("GENERATION_TEMPERATURE", "0.3"))
    max_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "256"))

    prompt = (
        "คุณคือระบบผู้ช่วยตอบปัญหาไอที 'ช่วยด้วย'\n"
        "โปรดนำผลการจำแนกประเภทคำถาม (Classification Result) ต่อไปนี้ "
        "มาอธิบายให้ผู้ใช้ฟังด้วยภาษาที่สุภาพ เข้าใจง่าย และสั้นกระชับ (ไม่เกิน 2 ประโยค) "
        "พร้อมแนะนำขั้นตอนถัดไปเบื้องต้น:\n\n"
        f"ผลลัพธ์: {req.draft or 'ไม่ทราบประเภท'}"
    )

    # ข้อ 3: วนลูปตามลำดับ LLM_PRIMARY -> LLM_FALLBACK
    providers = [os.getenv("LLM_PRIMARY", "groq"), os.getenv("LLM_FALLBACK", "gemini")]
    last_err = None

    for provider in providers:
        provider_str = provider.strip()
        if not provider_str:
            continue
        try:
            client, model_name = get_llm_client(provider_str)

            # ข้อ 2: ส่ง reasoning_effort = low เฉพาะเมื่อใช้งาน Groq
            extra = {"extra_body": {"reasoning_effort": "low"}} if provider_str == "groq" else {}

            response = await client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **extra
            )

            choice = response.choices[0]
            
            # ข้อ 2: บันทึก Log เมื่อคำตอบถูกตัดเนื่องจากสเปกยาวเกินกำหนด
            if choice.finish_reason == "length":
                jlog(event="answer_truncated", mode="explain_local", provider=provider_str)

            if choice.finish_reason == "content_filter":
                latency = int((time.perf_counter() - start_time) * 1000)
                return GenerateResponse(
                    request_id=req.request_id,
                    answer="คำขอถูกระงับเนื่องจากติดเงื่อนไขความปลอดภัย",
                    sources=[],
                    blocked=True,
                    block_reason="content_filter",
                    model=model_name,
                    latency_ms=latency,
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

            latency = int((time.perf_counter() - start_time) * 1000)
            return GenerateResponse(
                request_id=req.request_id,
                answer=safe_answer.strip(),
                sources=[],
                blocked=False,
                block_reason=None,
                model=model_name,
                latency_ms=latency,
                token_usage=usage,
            )
        except Exception as e:
            last_err = e
            jlog(event="llm_provider_failed", provider=provider_str, error=str(e)[:200])

    # หากพังหมดทุก Provider ให้สลับมาใช้คำตอบสำรองแทนการล่ม
    jlog(event="llm_error_all_providers", mode="explain_local", error=str(last_err))
    latency = int((time.perf_counter() - start_time) * 1000)
    return GenerateResponse(
        request_id=req.request_id,
        answer=mask_pii(req.draft or "ระบบได้ทำการจำแนกประเภทคำร้องของคุณแล้ว"),
        sources=[],
        blocked=False,
        block_reason=None,
        model="fallback-none",
        latency_ms=latency,
        token_usage=TokenUsage(),
    )


async def handle_grounded(req: GenerateRequest) -> GenerateResponse:
    """mode grounded: เรียก LLM เขียนคำตอบจาก contexts พร้อมระบบ Fallback และ Citation Verification"""
    start_time = time.perf_counter()
    temperature = float(os.getenv("GENERATION_TEMPERATURE", "0.2"))
    max_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))

    # เตรียม Context และ Prompt สำหรับ grounded
    context_str = ""
    if req.contexts:
        context_blocks = []
        for ctx in req.contexts:
            ref_id = getattr(ctx, 'ref', '')
            text = getattr(ctx, 'text', '')
            context_blocks.append(f"[{ref_id}] {text}")
        context_str = "\n".join(context_blocks)

    prompt = (
        "คุณคือระบบผู้ช่วยตอบปัญหาไอที 'ช่วยด้วย'\n"
        "โปรดตอบคำถามของผู้ใช้โดยอ้างอิงข้อมูลจากเอกสารบริบท (Context) ที่กำหนดให้อย่างแม่นยำ "
        "และระบุเลขบริบทอ้างอิงแบบ [n] ท้ายประโยคที่ใช้อ้างอิงเสมอ หากบริบทไม่พอตอบ ให้ตอบตามความเป็นจริง:\n\n"
        f"เอกสารบริบท:\n{context_str}\n\n"
        f"คำถาม/ร่างคำตอบ: {req.draft or ''}"
    )

    # ข้อ 3: วนลูปตามลำดับ LLM_PRIMARY -> LLM_FALLBACK
    providers = [os.getenv("LLM_PRIMARY", "groq"), os.getenv("LLM_FALLBACK", "gemini")]
    last_err = None

    for provider in providers:
        provider_str = provider.strip()
        if not provider_str:
            continue
        try:
            client, model_name = get_llm_client(provider_str)

            # ข้อ 2: ส่ง reasoning_effort = low เฉพาะเมื่อใช้งาน Groq
            extra = {"extra_body": {"reasoning_effort": "low"}} if provider_str == "groq" else {}

            response = await client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **extra
            )

            choice = response.choices[0]

            # ข้อ 2: บันทึก Log เมื่อคำตอบโดนตัดกลางประโยค
            if choice.finish_reason == "length":
                jlog(event="answer_truncated", mode="grounded", provider=provider_str)

            if choice.finish_reason == "content_filter":
                latency = int((time.perf_counter() - start_time) * 1000)
                return GenerateResponse(
                    request_id=req.request_id,
                    answer="คำขอถูกระงับเนื่องจากติดเงื่อนไขความปลอดภัย",
                    sources=[],
                    blocked=True,
                    block_reason="content_filter",
                    model=model_name,
                    latency_ms=latency,
                    token_usage=TokenUsage(),
                )

            raw_answer = choice.message.content or ""
            
            # ตรวจสอบและทำความสะอาด Citation + Mask PII
            cleaned_answer, valid_sources = verify_and_clean_citations(raw_answer, req.contexts or [])
            safe_answer = mask_pii(cleaned_answer)

            usage = TokenUsage()
            if response.usage:
                usage = TokenUsage(
                    input=response.usage.prompt_tokens,
                    output=response.usage.completion_tokens,
                )

            latency = int((time.perf_counter() - start_time) * 1000)
            return GenerateResponse(
                request_id=req.request_id,
                answer=safe_answer,
                sources=valid_sources,
                blocked=False,
                block_reason=None,
                model=model_name,
                latency_ms=latency,
                token_usage=usage,
            )
        except Exception as e:
            last_err = e
            jlog(event="llm_provider_failed", provider=provider_str, error=str(e)[:200])

    # หากล้มเหลวทุก Provider ให้คืน fallback response อย่างปลอดภัย
    jlog(event="llm_error_all_providers", mode="grounded", error=str(last_err))
    latency = int((time.perf_counter() - start_time) * 1000)
    return GenerateResponse(
        request_id=req.request_id,
        answer="เกิดข้อผิดพลาดในการเชื่อมต่อกับบริการ AI กรุณาลองใหม่อีกครั้ง",
        sources=[],
        blocked=False,
        block_reason=None,
        model="fallback-none",
        latency_ms=latency,
        token_usage=TokenUsage(),
    )


async def handle_grounded(req: GenerateRequest) -> GenerateResponse:
    """mode grounded: เรียก LLM เขียนคำตอบจาก contexts พร้อม [n] ที่ตรวจสอบได้จริง"""
    start_time = time.perf_counter()

    if not req.contexts:
        latency = int((time.perf_counter() - start_time) * 1000)
        return GenerateResponse(
            request_id=req.request_id,
            answer="ขออภัย ไม่พบข้อมูลที่เพียงพอในคลังความรู้สำหรับตอบคำถามนี้",
            sources=[],
            blocked=False,
            block_reason=None,
            model="none",
            latency_ms=latency,
            token_usage=TokenUsage(),
        )

    temperature = float(os.getenv("GENERATION_TEMPERATURE", "0.3"))
    max_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "1024"))

    template = jinja_env.get_template("grounded.j2")
    rendered_prompt = template.render(
        contexts=req.contexts,
        history=req.history,
        query=req.query,
    )

    try:
        # ข้อ 1: ย้าย get_llm_client() เข้ามาไว้ภายใน try block
        client, model_name = get_llm_client()

        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": rendered_prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            latency = int((time.perf_counter() - start_time) * 1000)
            return GenerateResponse(
                request_id=req.request_id,
                answer="เนื้อหาถูกระงับเนื่องจากเงื่อนไขความปลอดภัยของระบบ",
                sources=[],
                blocked=True,
                block_reason="content_filter",
                model=model_name,
                latency_ms=latency,
                token_usage=TokenUsage(),
            )

        raw_answer = choice.message.content or ""
        cleaned_answer, cited_sources = verify_and_clean_citations(raw_answer, req.contexts)
        final_answer = mask_pii(cleaned_answer)

        usage = TokenUsage()
        if response.usage:
            usage = TokenUsage(
                input=response.usage.prompt_tokens,
                output=response.usage.completion_tokens,
            )

        latency = int((time.perf_counter() - start_time) * 1000)
        return GenerateResponse(
            request_id=req.request_id,
            answer=final_answer.strip(),
            sources=cited_sources,
            blocked=False,
            block_reason=None,
            model=model_name,
            latency_ms=latency,
            token_usage=usage,
        )
    except Exception as e:
        # ข้อ 2: บันทึกลง Log แต่คืนค่า blocked=False, block_reason=None
        jlog(event="llm_error", mode="grounded", error=str(e))
        latency = int((time.perf_counter() - start_time) * 1000)
        return GenerateResponse(
            request_id=req.request_id,
            answer="เกิดข้อผิดพลาดในการเชื่อมต่อกับระบบประมวลผลภาษา กรุณาลองใหม่อีกครั้ง",
            sources=[],
            blocked=False,
            block_reason=None,
            model="error",
            latency_ms=latency,
            token_usage=TokenUsage(),
        )