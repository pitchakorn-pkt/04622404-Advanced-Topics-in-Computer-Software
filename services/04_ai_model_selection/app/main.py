"""04 AI Model Selection — General AI + Local AI

/general — เรียก LLM ผ่านไลบรารี openai (AsyncOpenAI) ชี้ base_url ไป Groq
พร้อม fallback provider, timeout, และเช็คโมเดลตอน startup ตาม CONTRACT §7
/local/classify — เชื่อมกับโมเดล intent classifier ที่เทรนจาก data/intents.csv
(TF-IDF word+char n-gram + LinearSVC ครอบด้วย CalibratedClassifierCV,
ผ่าน DoD ที่ CV accuracy 81.92%) โหลดจาก models/intent_v1.joblib แบบ lazy
+ cache ต่อ process ใช้ clf.predict_proba() ตรงๆ (ไม่ใช่ softmax เอง — แก้ตาม
code review ของ PR #8 ที่พบว่า score จาก decision_function เดิมต่ำเกินไปจน
ไม่ถึงเกณฑ์ CONTRACT ที่ router ต้องการ score >= 0.75 เลยแม้แต่ข้อเดียว)
สำคัญ: ต้องมี nlp_utils.py (โฟลเดอร์เดียวกับ train.py) อยู่บน sys.path ตอนรัน
service นี้ด้วย — joblib.load ต้อง import nlp_utils เพื่อคืนค่า thai_tokenizer
ที่ฝังอยู่ใน vectorizer ที่เซฟไว้ ถ้าหาไม่เจอ /local/classify จะพังเป็น 500
"""
import logging
import os
import time
from pathlib import Path

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from .common import error_body, forward_headers, health_payload, jlog, request_id_middleware  # noqa: F401
from .schemas import ClassifyRequest, EngineResult, GeneralRequest, TokenUsage

app = FastAPI(title="chuayduay · engines")
app.middleware("http")(request_id_middleware)

logger = logging.getLogger("engines")

# ---- ตาราง provider ตาม CONTRACT §7 ----
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.environ.get("GROQ_API_KEY", ""),
        "model": os.environ.get("GROQ_MODEL", ""),
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.environ.get("GEMINI_API_KEY", ""),
        "model": os.environ.get("GEMINI_MODEL", ""),
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "model": os.environ.get("OPENAI_MODEL", ""),
    },
}

PRIMARY = os.environ.get("LLM_PRIMARY", "groq")
FALLBACK = os.environ.get("LLM_FALLBACK", "gemini")

MAX_OUTPUT_TOKENS = int(os.environ.get("ENGINES_MAX_OUTPUT_TOKENS", "800"))
MAX_INPUT_CHARS = 12000

# router ให้เวลาโมดูลนี้รวมทั้งหมดประมาณ 30s (primary + fallback ถ้าจำเป็น)
# ตั้ง timeout ต่อ provider ไว้ที่ 12s และไม่ retry ซ้ำ provider เดิม (retry ผ่าน fallback แทน)
LLM_TIMEOUT_SECONDS = 12

TASK_INSTRUCTION = {
    "qa": "ตอบคำถามให้กระชับ ตรงประเด็น",
    "summarize": "สรุปเนื้อหาที่ได้รับให้สั้นและครบใจความสำคัญ",
    "write": "เขียนเนื้อหาตามที่ผู้ใช้ขอ",
}

SYSTEM_PROMPT = (
    "คุณเป็นผู้ช่วยแก้ปัญหามือถือและคอมพิวเตอร์ "
    "ตอบเป็นภาษาเดียวกับที่ผู้ใช้ใช้ถาม ตอบให้ชัดเจนและนำไปใช้ได้จริง"
)

_clients: dict[str, AsyncOpenAI] = {}

# ---- Local AI: intent classifier (train.py + data/intents.csv) ----
LOCAL_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "intent_v1.joblib"
_local_model_bundle: dict | None = None


def _get_local_model() -> dict:
    """โหลดโมเดล intent classifier แบบ lazy + cache (โหลดครั้งเดียวต่อ process)"""
    global _local_model_bundle
    if _local_model_bundle is None:
        _local_model_bundle = joblib.load(LOCAL_MODEL_PATH)
    return _local_model_bundle


def _get_client(provider: str) -> AsyncOpenAI:
    if provider not in _clients:
        cfg = PROVIDERS[provider]
        _clients[provider] = AsyncOpenAI(
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            timeout=LLM_TIMEOUT_SECONDS,
            max_retries=0,
        )
    return _clients[provider]


def _trim_context(history: list, file_text: str | None) -> tuple[list, str | None]:
    file_text = file_text or ""
    while history:
        total = sum(len(m.content) for m in history) + len(file_text)
        if total <= MAX_INPUT_CHARS:
            break
        history = history[1:]
    if len(file_text) > MAX_INPUT_CHARS:
        file_text = file_text[:MAX_INPUT_CHARS]
    return history, (file_text or None)


@app.on_event("startup")
async def check_primary_model():
    """เช็คว่าโมเดลหลักยังอยู่จริง — Groq เคยถอดโมเดลแบบไม่แจ้งมาแล้ว (18 ส.ค. 2026)"""
    cfg = PROVIDERS[PRIMARY]
    client = _get_client(PRIMARY)
    try:
        await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        jlog(event="startup_model_check", provider=PRIMARY, model=cfg["model"], status="ok")
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "STARTUP WARNING: primary model '%s' (provider=%s) ไม่ตอบสนอง — %s",
            cfg["model"], PRIMARY, str(e),
        )
        jlog(event="startup_model_check", provider=PRIMARY, model=cfg["model"],
             status="error", error=str(e))


@app.on_event("startup")
async def check_local_model():
    """เช็คว่าโมเดล intent classifier (train.py) โหลดได้จริงตั้งแต่ startup
    กันดีเลย์รอบแรกที่มีคนเรียก /local/classify และเห็น error เร็วถ้าลืม commit ไฟล์โมเดล
    """
    try:
        bundle = _get_local_model()
        jlog(event="startup_local_model_check", status="ok",
             path=str(LOCAL_MODEL_PATH), classes=list(bundle["classifier"].classes_))
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "STARTUP WARNING: โหลดโมเดล intent classifier ไม่สำเร็จที่ %s — %s "
            "(/local/classify จะตอบ 503 จนกว่าจะมีไฟล์โมเดล)",
            LOCAL_MODEL_PATH, str(e),
        )
        jlog(event="startup_local_model_check", status="error",
             path=str(LOCAL_MODEL_PATH), error=str(e))


@app.get("/health")
async def health():
    return health_payload()


@app.post("/general", response_model=EngineResult)
async def general(req: GeneralRequest):
    jlog(event="general", task=req.task, query_len=len(req.query))

    history, file_text = _trim_context(req.history, req.file_text)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history:
        messages.append({"role": m.role, "content": m.content})
    user_content = req.query
    if file_text:
        user_content = f"{req.query}\n\n===== เนื้อหาจากไฟล์ =====\n{file_text}"
    messages.append({"role": "user", "content": f"[{TASK_INSTRUCTION[req.task]}]\n{user_content}"})

    started = time.monotonic()
    used_provider = PRIMARY
    try:
        resp = await _get_client(PRIMARY).chat.completions.create(
            model=PROVIDERS[PRIMARY]["model"],
            messages=messages,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
    except (APITimeoutError, APIStatusError, APIConnectionError) as e:
        jlog(event="general_primary_failed", provider=PRIMARY, error=str(e))
        used_provider = FALLBACK
        try:
            resp = await _get_client(FALLBACK).chat.completions.create(
                model=PROVIDERS[FALLBACK]["model"],
                messages=messages,
                max_tokens=MAX_OUTPUT_TOKENS,
            )
        except (APITimeoutError, APIStatusError, APIConnectionError) as e2:
            jlog(event="general_fallback_failed", provider=FALLBACK, error=str(e2))
            raise

    latency_ms = int((time.monotonic() - started) * 1000)
    choice = resp.choices[0].message.content or ""
    model_used = PROVIDERS[used_provider]["model"]

    if used_provider != PRIMARY:
        jlog(event="general_used_fallback", provider=used_provider, model=model_used)

    return EngineResult(
        engine="general_ai",
        content=choice,
        data={},
        sources=[],
        model=model_used,
        latency_ms=latency_ms,
        token_usage=TokenUsage(
            input=resp.usage.prompt_tokens if resp.usage else 0,
            output=resp.usage.completion_tokens if resp.usage else 0,
        ),
    )


@app.post("/local/classify", response_model=EngineResult)
async def classify(req: ClassifyRequest):
    jlog(event="classify", text_len=len(req.text))
    started = time.monotonic()

    try:
        bundle = _get_local_model()
    except Exception as e:  # noqa: BLE001 — ครอบคลุมทั้งไฟล์หาไม่เจอและ unpickle ล้ม
        # unpickle ล้มบ่อยสุดเพราะ nlp_utils.py (thai_tokenizer) หาไม่เจอตอน
        # joblib.load — ดู docstring บนสุดของไฟล์นี้
        jlog(event="classify_model_missing", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=error_body("MODEL_NOT_LOADED", "โมเดล intent classifier ยังไม่พร้อมใช้งาน"),
        ) from e

    vectorizer, clf = bundle["vectorizer"], bundle["classifier"]

    X = vectorizer.transform([req.text])
    # clf คือ CalibratedClassifierCV ครอบ LinearSVC — predict_proba() ให้ค่าที่
    # ผ่านการ calibrate จริง (Platt scaling) ใช้เทียบกับเกณฑ์ CONTRACT (>= 0.75) ได้ตรงๆ
    probs = clf.predict_proba(X)[0]

    order = np.argsort(probs)[::-1]
    classes = clf.classes_
    top_label = str(classes[order[0]])
    top_score = float(probs[order[0]])
    top_k = [[str(classes[i]), float(probs[i])] for i in order[:3]]

    latency_ms = int((time.monotonic() - started) * 1000)
    jlog(event="classify_done", label=top_label, score=round(top_score, 4),
         latency_ms=latency_ms)

    return EngineResult(
        engine="local_ai",
        content=f"หมวด: {top_label} ({top_score:.2f})",
        data={"label": top_label, "score": top_score, "top_k": top_k},
        sources=[],
        model="intent_v1",
        latency_ms=latency_ms,
        token_usage=TokenUsage(),
    )