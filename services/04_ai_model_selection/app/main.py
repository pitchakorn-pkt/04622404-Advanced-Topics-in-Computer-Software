"""04 AI Model Selection — General AI + Local AI

STUB: ทุก endpoint ในไฟล์นี้ตอบค่าปลอมที่ "หน้าตาถูกตาม contract" เท่านั้น
เจ้าของโมดูลมาแทนด้วยของจริง โดยห้ามเปลี่ยนรูปแบบ request/response

ของจริงที่ต้องทำ (ดู docs/team/04_ai_model_selection.md)
  /general        เรียก LLM ผ่านไลบรารี openai ชี้ base_url ไป Groq + fallback
  /local/classify โมเดล TF-IDF + LogisticRegression ที่เทรนเอง 8 หมวด
"""
from fastapi import FastAPI

from .common import forward_headers, health_payload, jlog, request_id_middleware  # noqa: F401
from .schemas import ClassifyRequest, EngineResult, GeneralRequest, TokenUsage

app = FastAPI(title="chuayduay · engines")
app.middleware("http")(request_id_middleware)


@app.get("/health")
async def health():
    return health_payload()


@app.post("/general", response_model=EngineResult)
async def general(req: GeneralRequest):
    # STUB: replace -- ของจริงเรียก LLM แล้วคืนคำตอบ พร้อม token_usage จริงจาก provider
    jlog(event="general", task=req.task, query_len=len(req.query))
    return EngineResult(
        engine="general_ai",
        content=f"(ตัวอย่างจาก stub) ได้รับคำถาม: {req.query}",
        data={},
        sources=[],
        model="stub",
        latency_ms=1,
        token_usage=TokenUsage(),
    )


@app.post("/local/classify", response_model=EngineResult)
async def classify(req: ClassifyRequest):
    # STUB: replace -- ของจริงโหลดโมเดลตอน startup ครั้งเดียว แล้ว predict
    # label ต้องสะกดตรงกับ CONTRACT ข้อ 3 เป๊ะ ไม่งั้น router map ไม่เจอแล้วพังเงียบ
    jlog(event="classify", text_len=len(req.text))
    return EngineResult(
        engine="local_ai",
        content="หมวด: การเชื่อมต่อเครือข่าย (0.87)",
        data={"label": "connectivity", "score": 0.87,
              "top_k": [["connectivity", 0.87], ["device_performance", 0.08]]},
        sources=[],
        model="stub",
        latency_ms=1,
        token_usage=TokenUsage(),
    )
