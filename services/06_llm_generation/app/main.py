"""06 LLM Generation — ด่านสุดท้ายก่อนถึงผู้ใช้

STUB: ตอบข้อความปลอมตามโหมดที่ขอมา
ของจริงดู docs/team/06_llm_generation.md

สามโหมดคือสามงานคนละแบบ อย่าเขียนรวมเป็นฟังก์ชันเดียว
  grounded       เรียก LLM เขียนคำตอบจาก contexts พร้อม [n] ที่ตรวจสอบได้
  passthrough    **ไม่เรียก LLM** ทำแค่ safety + จัด markdown ของ draft แล้วคืน model="none"
  explain_local  เรียก LLM สั้น ๆ แปลงผล classifier เป็นประโยคคน
"""
from fastapi import FastAPI

from .common import health_payload, jlog, request_id_middleware  # noqa: F401
from .schemas import GenerateRequest, GenerateResponse, TokenUsage

app = FastAPI(title="chuayduay · generation")
app.middleware("http")(request_id_middleware)


@app.get("/health")
async def health():
    return health_payload()


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    jlog(event="generate", mode=req.mode, contexts=len(req.contexts))

    if req.mode == "passthrough":
        # STUB: replace -- ของจริงทำ safety + จัด markdown แต่ห้ามเรียก LLM
        return GenerateResponse(request_id=req.request_id, answer=req.draft or "",
                                sources=[], model="none", latency_ms=1,
                                token_usage=TokenUsage())

    if req.mode == "explain_local":
        # STUB: replace
        return GenerateResponse(request_id=req.request_id,
                                answer=req.draft or "(stub) อธิบายผลการจำแนก",
                                sources=[], model="stub", latency_ms=1,
                                token_usage=TokenUsage())

    # grounded — ของจริงต้องตรวจ [n] ทุกตัวว่ามีอยู่ใน contexts จริง ตัวที่ไม่มีให้ตัดทิ้ง
    cited = [c.source for c in req.contexts[:2]]
    marks = " ".join(f"[{c.ref}]" for c in req.contexts[:2])
    return GenerateResponse(
        request_id=req.request_id,
        answer=f"(ตัวอย่างจาก stub) ตอบจากเอกสารที่ค้นเจอ {marks}".strip(),
        sources=cited, model="stub", latency_ms=1, token_usage=TokenUsage(),
    )
