# 03 AI Router / Agent

compose service: `router` · ฟัง `0.0.0.0:8000` ข้างใน container · ทดสอบที่ `localhost:8003`

รับ `POST /route` จาก 02 api ตัดสินใจว่าคำถามควรไปเส้นไหน แล้วเรียก 04 / 05 / 06 ตามเส้นนั้น
รวมผลกลับไปพร้อม `reasoning`, `confidence`, `trace` และ `token_usage` ของทุก hop

## ตัดสินใจยังไง — cascade 4 ชั้น หยุดทันทีที่มั่นใจพอ

| ชั้น | ไฟล์ | ตัดสินใจจาก | เรียก LLM |
|---|---|---|---|
| 0 guard | `app/guard.py` | ว่าง / สั้นเกิน / อ้างอิงลอย ๆ → `clarify` · คำขอที่ไม่ควรตอบ → `decline` | ไม่ |
| 1 rules | `app/rules.py` | ตาราง keyword ที่ล็อกไว้ 6 หมวด → `university_rag` (0.9) · คำสั่งจำแนก → `local_ai` | ไม่ |
| 2 classifier | `app/cascade.py` | 04 `/local/classify` ถ้า `score ≥ 0.75` แปลงหมวดเป็น route ตาม CONTRACT §3 | ไม่ |
| 3 llm | `app/llm.py` | ถาม LLM ให้ตอบ JSON · `confidence < 0.5` → `clarify` | ใช่ |

ทุก request บันทึก `decided_at_layer` ลง log และส่งกลับใน `trace` — ตัวเลขนี้เก็บย้อนหลังไม่ได้ถ้าไม่ใส่ตั้งแต่แรก

**ชั้น 1 ตอบเฉพาะตอนมั่นใจ** ไม่เจอคำในตารางจะเงียบแล้วปล่อยให้ชั้น 2 ทำต่อ ไม่เดาว่าเป็น `general_other` เอง
เทียบ keyword แบบดูขอบเขตคำที่ `pythainlp` ตัดให้ ไม่ใช่ substring — ไม่งั้น "จอ" จะไปตรงกับ "จอง"

## เส้นทางของแต่ละ route (`app/plans.py`)

| route | ทำอะไร |
|---|---|
| `university_rag` | (rewrite ถ้าเป็น follow-up) → 05 `/search` → ใส่เลข `ref` 1..n → 06 `/generate` mode `grounded` |
| `general_ai` | 04 `/general` → 06 `/generate` mode `passthrough` (ไม่เรียก LLM ซ้ำ) |
| `local_ai` | 04 `/local/classify` → 06 `/generate` mode `explain_local` |
| `clarify` | ถามกลับ 1 ข้อจาก template ไม่เรียกใคร |
| `decline` | ปฏิเสธอย่างสุภาพ + ช่องทางติดต่อเจ้าหน้าที่ ไม่เรียกใคร |

**ถ้า retrieval คืน `chunks` ว่าง หรือ 05 ล่ม** → ตอบด้วย `general_ai` แล้วต่อท้ายว่า
"คำตอบนี้มาจากความรู้ทั่วไป ไม่ได้อ้างอิงเอกสารในคลังความรู้" (CONTRACT §3 — ห้ามตอบ "ไม่พบ" ทันที)
**ถ้า 06 ล่ม** → ยังส่งชื่อเอกสารที่ค้นเจอกลับไปให้ผู้ใช้ ดีกว่าตอบว่าไม่มีอะไรเลย

## งบเวลา 70 วินาที (`app/budget.py`)

api รอเราไว้ 75s เราต้องจบก่อน 70s ไม่งั้นผู้ใช้เห็น 504 ทั้งที่คำตอบกำลังจะเสร็จ
timeout ต่อ hop ใน CONTRACT §0 เป็น "เพดาน" — เวลาจริงที่ให้แต่ละ hop คือ `min(เพดาน, เวลาที่เหลือ − 1s)`
เหลือไม่ถึง 1.5s ไม่เริ่ม hop ใหม่ ตัดจบแล้วตอบเท่าที่มี · rewrite คำถาม follow-up จำกัดที่ 10s

## วัดผล

```bash
python -m pytest tests -q                              # 48 เคส ครอบคลุมชั้น 0-3 และ fallback ทุกเส้น
python tests/eval_routing.py --offline                 # เฉพาะชั้น 0-1 ไม่ยิง service ไหนเลย
ENGINES_URL=http://localhost:8004 python tests/eval_routing.py   # cascade เต็ม (ต้องมี engines + API key)
```

`tests/routing_cases.jsonl` มี 40 ข้อ ครบทั้ง 5 route (rag 16 · general 8 · local 4 · clarify 6 · decline 6)
สคริปต์พิมพ์ accuracy แยกราย route, confusion matrix, และสัดส่วนที่ตัดสินใจได้โดยไม่เรียก LLM

### ผลที่วัดได้

| ชุดที่วัด | route accuracy | ตัดสินใจโดยไม่เรียก LLM | เวลาตัดสินใจเฉลี่ย |
|---|---|---|---|
| ชั้น 0-1 เท่านั้น (`--offline`) | 25/40 = 62.5% | 24/40 (60%) | 8 ms |
| cascade เต็ม 4 ชั้น | _ยังไม่ได้วัด — รอ engines ของจริง + `GROQ_API_KEY`_ | | |

ในโหมด offline ไม่มีข้อไหน misroute เลย — 15 ข้อที่ยังไม่ตรงคือข้อที่ชั้น 0-1 ไม่ตัดสินใจ
แล้วตกไป `clarify` ตามค่า default ซึ่งเป็นพฤติกรรมที่ตั้งใจ (ชั้น rules ต้องแม่น ไม่ใช่ตอบทุกข้อ)

**แก้ตาราง keyword ใน `app/rules.py` ทีไร ต้องรันชุดนี้ใหม่ทุกครั้ง** เพิ่มทีละคำแล้วดูว่า accuracy ขึ้นหรือลง

## รันเดี่ยว

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
curl localhost:8000/health
```

## รันในระบบรวม

```bash
docker compose up -d --wait
docker compose logs -f router
curl -s localhost:8003/route -H 'Content-Type: application/json' -d '{
  "request_id":"test-1","session_id":"s-1","user":{"id":"u-1"},
  "query":"ต่อไวไฟไม่ได้ ควรไล่ตรวจอะไรก่อน","history":[]}' | python -m json.tool
```

แก้ไฟล์ใน `app/` แล้ว reload ให้เองภายในไม่กี่วินาที · แก้ `requirements.txt` ต้อง `docker compose up -d --build router`

## ไฟล์ที่ห้ามแก้

`app/common.py` เป็นของกลาง (health / X-Request-ID / log JSON)
`Dockerfile` เป็นของหัวหน้า ต้องเพิ่ม system package ให้บอกก่อน

## Definition of Done

- [ ] route accuracy ≥ 85% บน 40 ข้อ (รอวัดด้วย cascade เต็ม)
- [x] ครบ 5 route ทำงานกับ stub — ยังต้องทดสอบกับของจริงอีกรอบ
- [x] ปิด 05 แล้วระบบยังตอบได้ พร้อมบอกผู้ใช้ว่าไม่ได้อ้างอิงเอกสาร (`test_retrieval_down_still_answers_with_warning`)
- [x] log แต่ละ request บอกชั้นที่ตัดสินใจ + เวลาต่อ hop (`decided_at_layer` + `trace.steps`)
- [ ] เส้น rag ที่ช้าที่สุดที่วัดได้ ยังต่ำกว่า 70 วินาที (รอวัดกับ 05/06 ของจริง)
