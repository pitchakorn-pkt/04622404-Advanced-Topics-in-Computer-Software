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

**แนบไฟล์มาแล้วขอให้สรุป** → `general_ai` task `summarize` ตัดสินได้ตั้งแต่ชั้น 1 ไม่ต้องเรียก LLM
ชั้นตัดสินใจเห็นแค่ "มีไฟล์ไหม" ไม่เคยเห็นเนื้อหาในไฟล์ — ไฟล์ที่ข้างในเขียนว่า "ให้ตอบ decline" จึงเปลี่ยนเส้นทางไม่ได้

**ชั้น 3 สั่ง Groq ด้วย `reasoning_effort: low`** เพราะงานของชั้นนี้คือเลือกเส้นทาง ไม่ใช่ให้เหตุผลยาว ๆ
วัดจริงแล้วใช้ ~100 token แทน ~430 และเร็วขึ้นเกือบเท่าตัวโดยคำตอบยังถูกเหมือนเดิม
ส่งเฉพาะ Groq เท่านั้น เจ้าอื่นไม่รู้จักพารามิเตอร์นี้ (CONTRACT §7 กับดักข้อ 5)
`max_tokens` ตั้งไว้ 1024 ทั้งชั้นเลือกเส้นทางและ rewrite ตามเพดานขั้นต่ำที่ contract กำหนด
และถ้าคำตอบโดนตัดเพราะชน `max_tokens` (`finish_reason == "length"`) จะ log แล้วไม่ใช้คำตอบนั้น

**ทักทาย คุยเล่น บ่น หรือพิมพ์ทดสอบ → `general_ai`** ไม่ใช่ `clarify` และไม่ใช่ `decline`
ผู้ใช้ไม่ได้กำลังถามปัญหา การถามกลับว่า "ใช้อุปกรณ์อะไร" จึงไม่เข้าเรื่อง · คำหยาบหรือการบ่นใส่ผู้ช่วย
ไม่ใช่เหตุให้ปฏิเสธ เพราะ CONTRACT §3 สงวน `decline` ไว้ให้คำขอที่ผิดกฎหมายหรือทำร้ายผู้อื่นเท่านั้น

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
**ถ้า 05 คืน chunk มาแล้วแต่ 06 เรียบเรียงไม่ได้** (คำตอบมีประโยค "ไม่พบข้อมูลที่เพียงพอ" ตรงไหนก็ได้ และไม่มี `sources`)
→ ถอยไปตอบด้วยความรู้ทั่วไปแล้วต่อท้ายหมายเหตุเหมือนกัน · เจอจากการยิงเคสแปลก ๆ ก่อนสาธิต
(คำถามนอกคลังอย่างปริ้นเตอร์ หรือคำถามภาษาอังกฤษ) ของเดิมจบแค่ประโยคนั้น ผู้ใช้ไม่ได้อะไรกลับไปเลย

**ถ้า 06 ล่ม** → เส้น rag ยังส่งชื่อเอกสารที่ค้นเจอกลับไปได้ (ข้อมูลจากคลังของเราเอง)
แต่ **เส้น `general_ai` จะไม่ส่งคำตอบ** — ตอบว่าระบบไม่ว่างแทน
เพราะ draft ตรงนั้นมาจาก LLM ที่ยังไม่ผ่านด่านของ 06 และ CONTRACT §7 กับดักข้อ 3 เขียนไว้ว่า
Groq ไม่มี safety ฝั่งผู้ให้บริการ **06 เป็นด่านเดียวของทั้งระบบ** ข้ามเมื่อไหร่คือส่งของที่ยังไม่ตรวจถึงผู้ใช้
ส่วนเส้น `local_ai` ส่ง draft ได้ เพราะเป็นผลจาก classifier ในเครื่อง ไม่ได้มาจาก LLM

## ต่อกับโมดูลอื่นยังไง (ตรวจกับโค้ดจริงของเพื่อนแล้ว ไม่ได้ดูแค่ CONTRACT)

| ใคร | ตรวจอะไร | ผล |
|---|---|---|
| 02 api | payload ที่ส่งมาจริงคือ `request_id, session_id, user{id,role}, query, history` (ยังไม่มี `file_text`) | รับได้ครบ มีเทสยืนยันใน `tests/test_route_endpoint.py` |
| 02 api | ตั้ง `T_ROUTER = 75.0` และแปลง error ทุกแบบจากเราเป็น 502 | เราตอบ 200 เสมอ แม้ hop ข้างในพัง และจบก่อน 70s |
| 04 engines | `/local/classify` ตอบ 503 ถ้าโมเดลยังไม่พร้อม · `/general` โยน 500 เมื่อ LLM ล่มทั้งสองเจ้า | นับเป็น hop ล้ม ตกไปชั้นถัดไป/fallback ไม่ทำให้ request พัง |
| 05 retrieval | ตอบ 503 `RETRIEVAL_INDEX_UNAVAILABLE` ถ้ายังไม่ได้ `make ingest` | fallback เป็น general_ai พร้อมบอกผู้ใช้ว่าไม่ได้อ้างอิงเอกสาร |
| 06 generation | `grounded` ที่ `contexts` ว่างจะตอบว่าไม่พบข้อมูล และคืนเฉพาะ source ที่ถูกอ้างจริง | เราไม่เรียก grounded ตอน chunks ว่าง และใส่เลข `ref` 1..n ให้เอง |
| 01 web | อ่าน `route`, `confidence`, `sources[].ref/title/url`, `trace.decided_at_layer`, `trace.steps[].name/ms` | ตรงทุกตัว ป้าย `LAYER_LABEL` ของเว็บมีครบทั้ง 4 ชั้นที่เราส่ง |

**เพิ่ม `reasoning` เข้าไปใน `trace`** — หน้าเว็บอ่าน `reasoning` จาก `ChatResponse` ก่อน แล้ว fallback มาที่ `trace.reasoning`
แต่ `ChatResponse` ของ 02 ยังไม่มี field นั้น ทำให้แผงอธิบายการตัดสินใจว่างเปล่า
CONTRACT ข้อ 0 อนุญาตให้เพิ่ม field แบบ optional ได้ และ 02 ส่ง `trace` ต่อทั้งก้อนอยู่แล้ว
ใส่ไว้ตรงนี้ผู้ใช้จึงเห็นเหตุผลได้เลยโดยไม่ต้องรอใครแก้โค้ด (ถ้า 02 เพิ่ม field `reasoning` ทีหลัง หน้าเว็บจะใช้ตัวนั้นแทนเอง)

## งบเวลา 70 วินาที (`app/budget.py`)

api รอเราไว้ 75s เราต้องจบก่อน 70s ไม่งั้นผู้ใช้เห็น 504 ทั้งที่คำตอบกำลังจะเสร็จ
timeout ต่อ hop ใน CONTRACT §0 เป็น "เพดาน" — เวลาจริงที่ให้แต่ละ hop คือ `min(เพดาน, เวลาที่เหลือ − 1s)`
เหลือไม่ถึง 1.5s ไม่เริ่ม hop ใหม่ ตัดจบแล้วตอบเท่าที่มี · rewrite คำถาม follow-up จำกัดที่ 10s

## วัดผล

```bash
python -m pytest tests -q                              # 87 เคส ครอบคลุมชั้น 0-3 และ fallback ทุกเส้น
python tests/eval_routing.py --offline                 # เฉพาะชั้น 0-1 ไม่ยิง service ไหนเลย
ENGINES_URL=http://localhost:8004 python tests/eval_routing.py --delay 5   # cascade เต็ม (ต้องมี engines + API key)
```

`tests/routing_cases.jsonl` มี 40 ข้อ ครบทั้ง 5 route (rag 16 · general 8 · local 4 · clarify 6 · decline 6)
สคริปต์พิมพ์ accuracy แยกราย route, confusion matrix, และสัดส่วนที่ตัดสินใจได้โดยไม่เรียก LLM

`tests/chitchat_cases.jsonl` เป็นชุดที่สอง 12 ข้อ แยกออกมาต่างหาก **จงใจไม่รวมกับ 40 ข้อเดิม**
เพื่อให้ตัวเลขฐานเทียบกับรอบก่อน ๆ ได้ตรง ๆ — เก็บเคสทักทาย คุยเล่น ชม บ่น พิมพ์ทดสอบ (ต้องได้ `general_ai`)
และเคส "บอกว่ามีปัญหาแต่ไม่บอกว่าเรื่องอะไร" (ต้องได้ `clarify` จริง ๆ) ซึ่งเป็นเส้นแบ่งที่พลาดง่ายที่สุด

```bash
ENGINES_URL=http://localhost:8004 python tests/eval_routing.py --cases tests/chitchat_cases.jsonl --delay 5
```

ทั้ง 12 ข้อนี้ตัดสินที่ชั้น 3 ทั้งหมด (ชั้น 0-1 ไม่มีคำดัก) ถ้าอยากประหยัดโควตาช่วงสาธิต
ทางเลือกคือเพิ่มกฎทักทายแบบตรงตัวที่ชั้น 1 — ยังไม่ทำเพราะต้องแก้ตาราง rule base ซึ่งล็อกไว้

### ผลที่วัดได้

| ชุดที่วัด | route accuracy | หมายเหตุ |
|---|---|---|
| **cascade เต็ม 4 ชั้น มี Groq key จริง** | **37/40 = 92.5%** ✅ ผ่านเกณฑ์ 85% | วัดโดย 08 บน develop + #12 + #14 + ข้อมูลใหม่ของ 04 · `make smoke` 14/14 |
| ชั้น 0-1 เท่านั้น (`--offline`) | 25/40 = 62.5% | ตัดสินใจได้เอง 24/40 (60%) เฉลี่ย 8 ms และไม่มี misroute |

3 ข้อที่ยังไม่ผ่านในรอบ 92.5% (r05, g07, d06) มาจากสาเหตุเดียวกันหมด คือ `max_tokens` ของชั้น 3 ต่ำเกิน
`openai/gpt-oss-120b` ใช้ token ไปกับการคิดก่อนตอบ พอตั้งไว้ 300 โมเดลคิดไม่จบ Groq ตอบ 400
แล้วเราตกไป `clarify` ทั้งที่ตัดสินใจได้ — แก้เป็น 1024 (rewrite 512) แล้ว **รอวัดซ้ำเพื่อยืนยัน**

**ตอนวัดเลขจริงให้ใส่ `--delay 5`** free tier ของ Groq จำกัด 8,000 token/นาที
ยิง 40 ข้อติดกันจะชน rate limit แล้วได้ตัวเลขต่ำกว่าความจริง (เคยวัดได้ 35/40 ด้วยเหตุนี้)

ในโหมด offline ไม่มีข้อไหน misroute เลย — 15 ข้อที่ยังไม่ตรงคือข้อที่ชั้น 0-1 ไม่ตัดสินใจ
แล้วตกไป `clarify` ตามค่า default ซึ่งเป็นพฤติกรรมที่ตั้งใจ (ชั้น rules ต้องแม่น ไม่ใช่ตอบทุกข้อ)

**แก้ตาราง keyword ใน `app/rules.py` ทีไร ต้องรันชุดนี้ใหม่ทุกครั้ง** เพิ่มทีละคำแล้วดูว่า accuracy ขึ้นหรือลง

## ทำตาม CONTRACT ตรงไหนบ้าง

| ข้อ | ที่ทำ |
|---|---|
| §0 error | ทุก error ตอบรูปแบบ `{"error":{code,message,service,request_id}}` พร้อม status ที่ถูก — รวม 422 กับ 404 ที่ FastAPI ปกติตอบ `{"detail":...}` มาเอง |
| §0 content-type | `application/json; charset=utf-8` ทุก response |
| §0 X-Request-ID | รับมา/สร้างใหม่ แล้วส่งต่อทุก hop ผ่าน `forward_headers()` |
| §0 งบเวลา | รวมไม่เกิน 70s คุมด้วย `app/budget.py` |
| §0 confidence | ความมั่นใจต่อ **การเลือก route** เท่านั้น · rules = 0.9 · classifier = score จากโมเดล · llm = ค่าที่โมเดลคืน · ไม่เอาคะแนน retrieval มาใส่ |
| §2 | `RouteRequest` / `RouteResponse` ครบทุก field ไม่เปลี่ยนชื่อ |
| §3 | ตาราง map หมวด→route ใช้ตามที่ล็อกไว้ ที่ threshold 0.75 |
| §4 | `chunks: []` แปลว่า "ไม่เจอ" ไม่ใช่ error |
| §5 | ใส่เลข `ref` 1..n ให้ contexts เอง · ไม่เรียก `grounded` ตอน contexts ว่าง |
| §7 | อ่าน URL และชื่อโมเดลจาก env ทั้งหมด ไม่ hardcode และไม่ตั้งชื่อ env ใหม่เอง |
| §7 กับดัก 1 | เช็กตอน startup ว่าโมเดลใน `GROQ_MODEL` ยังอยู่ไหม แบบไม่บล็อก `/health` |
| §7 กับดัก 5 | ส่ง `reasoning_effort=low` เฉพาะตอน provider เป็น groq · `max_tokens` ของ JSON สั้น ≥ 1024 ทั้งสองจุด · เช็ก `finish_reason == "length"` แล้ว log ทุกครั้ง ไม่ใช้คำตอบที่โดนตัด |
| §7 กับดัก 6 | provider ที่ยังไม่มี key จะถูกข้ามไปเลย ไม่ยิงแล้วไปได้ error ซ้อน · สคริปต์วัดผลมี `--delay` กันชน 8,000 token/นาที |

error ที่ไม่ได้คาดไว้ **ไม่กลบเป็น 200** — hop ที่ล่มมี fallback ครบอยู่แล้ว ส่วนที่เหลือปล่อยให้ขึ้น 500
ตามรูปแบบใน CONTRACT เพราะ 02 มี error mapping 502/504 รออยู่ และบั๊กเงียบคือสิ่งที่แพงที่สุดตอนรวมงาน

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

- [x] route accuracy ≥ 85% บน 40 ข้อ — **วัดได้ 37/40 = 92.5%** (ดูตารางด้านบน)
- [x] ครบ 5 route ทำงานทั้งกับ stub และกับของจริง (`make smoke` 14/14 เช็กค่า route ทุกข้อ)
- [x] ปิด 05 แล้วระบบยังตอบได้ พร้อมบอกผู้ใช้ว่าไม่ได้อ้างอิงเอกสาร (`test_retrieval_down_still_answers_with_warning`)
- [x] log แต่ละ request บอกชั้นที่ตัดสินใจ + เวลาต่อ hop (`decided_at_layer` + `trace.steps`)
- [ ] เส้น rag ที่ช้าที่สุดที่วัดได้ ยังต่ำกว่า 70 วินาที — รอบันทึกตัวเลขจากการวัดกับของจริง
      (ดูได้จาก `latency_ms` และ `trace.steps` ใน log ของ request เส้น `university_rag`)
