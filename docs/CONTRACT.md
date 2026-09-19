# CONTRACT.md — ข้อตกลง API ระหว่าง service ของ **ช่วยด้วย (ChuayDuay)** · v1.4

> **กฎเหล็ก**: แก้ไฟล์นี้ได้ผ่าน PR เท่านั้น ต้องได้ approve จากหัวหน้า + เจ้าของ service ทั้งสองฝั่งที่เกี่ยวข้อง
> เพิ่ม field ใหม่แบบ optional ได้ (ไม่ทำให้คนอื่นพัง) แต่ **ห้ามลบ/เปลี่ยนชื่อ field** โดยไม่แจ้ง

## 0. กติการ่วมทุก service
- Content-Type: `application/json; charset=utf-8` (ภาษาไทยต้องไม่เพี้ยน)
- Header `X-Request-ID`: ถ้าไม่มีให้สร้าง UUID แล้ว **ส่งต่อทุกครั้ง** ที่เรียก service อื่น และใส่ใน log ทุกบรรทัด
- `GET /health` → `200 {"status":"ok","service":"<name>","version":"<git-sha หรือ 0.1.0>"}`
- Error ทุกกรณีตอบรูปแบบเดียว + HTTP status ที่ถูกต้อง (400/401/404/413/422/429/500/502/504)
```json
{ "error": { "code": "ROUTER_TIMEOUT", "message": "คำอธิบายสั้น", "service": "api", "request_id": "..." } }
```
- Timeout (คนเรียกต้องตั้ง): web→api 90s, api→router 75s, router→engines/generation 30s, router→retrieval 15s
- เวลา: ISO-8601 เขต Asia/Bangkok เช่น `2026-09-18T14:03:00+07:00`
- ID ทุกตัวเป็น UUID string
- **งบเวลาภายใน router**: timeout ต่อ hop ข้างบนเป็น "เพดานต่อ hop" ไม่ใช่งบรวม — router ต้องคุมเวลารวมของทุก hop **ไม่เกิน 70 วินาที** (ต่ำกว่า 75s ที่ api รอไว้ 5 วินาที) ถ้าจะเรียก LLM เพิ่ม เช่น rewrite คำถาม follow-up ให้ตั้ง timeout ของขั้นนั้น ≤ 10s และนับรวมในงบ 70s
- **`confidence` หมายถึงอะไร**: ความมั่นใจของ **router ต่อการเลือก route** เท่านั้น ไม่ใช่ความมั่นใจว่าคำตอบถูก · ชั้น rules = 0.9, ชั้น classifier = score จากโมเดล, ชั้น LLM = ค่าที่ LLM คืน · ค่านี้ไหลผ่าน api ไปถึงหน้าเว็บโดยไม่แปลงความหมาย

## Object ที่ใช้ร่วม
```json
// Source — ใช้ทุกที่ที่มีการอ้างอิง
{ "ref": 1, "doc_id": "it-wifi-001", "title": "ต่อ Wi-Fi ไม่ได้ — ไล่ตรวจทีละขั้น", "url": "https://...", "page": 3, "date": "2026-05-01", "category": "it_support" }

// TokenUsage
{ "input": 0, "output": 0 }

// Trace — optional แต่ทุกคนบนเส้นทางต้องส่งต่อ ใช้โชว์ว่า agent ตัดสินใจยังไงบนหน้าเว็บ
// เป็นจุดที่ทำให้ระบบ "ดูเป็น agent" ไม่ใช่กล่องดำ ไม่มีต้นทุนเพิ่มเพราะข้อมูลไหลผ่านอยู่แล้ว
{
  "decided_at_layer": "rules",                 // guard | rules | classifier | llm
  "steps": [
    { "name": "router.rules",      "ms": 3 },
    { "name": "retrieval.search",  "ms": 340 },
    { "name": "generation.grounded","ms": 1520 }
  ]
}

// HistoryMessage
{ "role": "user | assistant", "content": "..." }
```
`route` ใช้ค่าได้แค่: `general_ai` | `university_rag` | `local_ai` | `clarify` | `decline`

> **เรื่องชื่อ `university_rag`** — โดเมนข้อมูลของเราไม่ใช่เอกสารมหาวิทยาลัย (อาจารย์ยืนยันแล้วว่าใช้ข้อมูลอะไรก็ได้)
> แต่**คงชื่อค่า enum ไว้ตามผังอาจารย์** เพราะแมปกับกล่อง "University RAG" ในแผนภาพเขาหนึ่งต่อหนึ่ง และการเปลี่ยนชื่อกระทบ 01, 03, 07 พร้อมกันโดยไม่ได้อะไรกลับมา
> ความหมายจริงคือ **"เส้นทางที่ตอบจากคลังความรู้ที่เราดูแลเอง พร้อมอ้างอิง"**
> **หน้าเว็บห้ามโชว์ค่า enum ดิบ** ให้แปลงเป็นป้ายที่คนอ่านรู้เรื่อง — `university_rag` → "ตอบจากคลังความรู้" · `general_ai` → "ความรู้ทั่วไป" · `local_ai` → "โมเดลในเครื่อง" · `clarify` → "ขอข้อมูลเพิ่ม" · `decline` → "ปฏิเสธ"
`category` ของเอกสาร: `it_support` | `howto` | `faq` | `policy` | `other`
(`it_support` = คู่มือแก้ปัญหาอุปกรณ์/บัญชี/เครือข่าย · `howto` = บทความสอนทำทีละขั้น · `policy` = ข้อกำหนด/ข้อควรรู้ · ที่มาของข้อมูลอยู่ใน `05_retrieval_knowledge.md`)

---

## 1. web → api (public, prefix `/api`)
auth ใช้ httpOnly cookie ชื่อ `access_token` (JWT)

| Method | Path | Request | Response 200 |
|---|---|---|---|
| POST | `/api/auth/login` | `{username, password}` | `{user:{id,username,display_name,role}}` + set cookie |
| POST | `/api/auth/logout` | – | `{ok:true}` |
| GET | `/api/auth/me` | – | `{user:{...}}` หรือ 401 |
| POST | `/api/chat` | `ChatRequest` | `ChatResponse` |
| POST | `/api/upload` | multipart `file` (pdf/png/jpg/docx ≤10MB) | `{file_id, filename, mime, pages, chars}` |
| GET | `/api/sessions` | – | `{sessions:[{session_id,title,updated_at}]}` |
| GET | `/api/history/{session_id}` | – | `{session_id, messages:[Message]}` |
| POST | `/api/feedback` | `{message_id, rating: 1 or -1, comment?}` | `{ok:true}` |
| GET | `/api/stats?days=7` | – | ส่งต่อจาก response-log `/stats?days=` (ค่า default 7) |

```json
// ChatRequest
{ "session_id": "uuid หรือ null (null = เริ่มบทสนทนาใหม่)", "message": "ต่อไวไฟไม่ได้ ควรไล่ตรวจอะไรก่อน", "file_ids": [] }
// แนบได้หลายไฟล์: api ต่อข้อความของแต่ละไฟล์เรียงตามลำดับใน file_ids คั่นด้วยบรรทัด
//   ===== ไฟล์: <filename> =====
// แล้วตัดรวมทั้งก้อนไม่เกิน 20000 ตัวอักษร (ตัดท้าย) ก่อนส่งเป็น file_text ให้ router

// ChatResponse
{
  "request_id": "uuid", "session_id": "uuid", "message_id": "uuid",
  "answer": "markdown text พร้อม [1] [2]",
  "sources": [ Source ],
  "route": "university_rag", "engines_used": ["retrieval","generation"],
  "confidence": 0.91, "latency_ms": 4200, "created_at": "...",
  "trace": Trace
}

// Message (ใน history)
{ "message_id": "uuid", "role": "user|assistant", "content": "...", "sources": [], "route": "...", "rating": 1, "created_at": "..." }
```

## 2. api → router
`POST /route`
```json
// RouteRequest
{
  "request_id": "uuid", "session_id": "uuid",
  "user": { "id": "uuid", "role": "student", "faculty": "engineering" },
  "query": "ข้อความผู้ใช้",
  "history": [ HistoryMessage ],           // ข้อความ "ล่าสุด" ไม่เกิน 10 รายการ แต่เรียง เก่า→ใหม่
                                           // api แปลงมาจาก Message ของ 07 (เอาแค่ role + content)
  "file_text": "ข้อความที่ extract จากไฟล์ (optional, ตัดไม่เกิน 20000 ตัวอักษร)"
}
// RouteResponse
{
  "request_id": "uuid",
  "answer": "...", "sources": [ Source ],
  "route": "university_rag", "engines_used": ["retrieval","generation"],
  "confidence": 0.91, "reasoning": "เจอคำว่า ไวไฟ ในชั้น rules",
  "latency_ms": 3900, "token_usage": TokenUsage,
  "trace": Trace
}
```

## 3. router → engines
`POST /general`
```json
{ "request_id": "uuid", "query": "...", "history": [ HistoryMessage ], "file_text": "optional", "task": "qa | summarize | write" }
```
`POST /local/classify`
```json
{ "request_id": "uuid", "text": "..." }
```
ทั้งสองตอบ `EngineResult`
```json
{
  "engine": "general_ai | local_ai",
  "content": "ข้อความผลลัพธ์ (local: สรุปเป็นคำอ่านได้ เช่น 'หมวด: การเชื่อมต่อเครือข่าย (0.87)')",
  "data": { "label": "connectivity", "score": 0.87, "top_k": [["connectivity",0.87],["device_performance",0.08]] },
  "sources": [],
  "model": "openai/gpt-oss-120b | tfidf-logreg-v1",   // ชื่อโมเดลที่ใช้จริง ไม่ใช่ชื่อ provider
  "latency_ms": 800, "token_usage": TokenUsage
}
```
หมวดของ classifier (v1) — **8 หมวด ตรงกับหมวดในคลังความรู้จริง**:
`connectivity`, `account_security`, `device_performance`, `data_backup`, `apps_updates`, `hardware_media`, `general_other`, `out_of_scope`

**ตาราง map หมวด → route (ล็อกแล้ว ห้ามตีความเอง)** — 03 ใช้ตารางนี้ที่ชั้น classifier, 04 ต้องไม่เพิ่ม/เปลี่ยนชื่อหมวดโดยไม่แก้ตารางนี้ผ่าน PR

| หมวดจาก classifier | route ที่ต้องไป | หมายเหตุ |
|---|---|---|
| `connectivity` | `university_rag` | ไวไฟ เน็ต การเชื่อมต่อ |
| `account_security` | `university_rag` | บัญชี รหัสผ่าน มิจฉาชีพ |
| `device_performance` | `university_rag` | เครื่องช้า พื้นที่เต็ม แบตเตอรี่ |
| `data_backup` | `university_rag` | ข้อมูลหาย การสำรองข้อมูล |
| `apps_updates` | `university_rag` | แอป การอัปเดต |
| `hardware_media` | `university_rag` | จอ เสียง กล้อง ฮาร์ดแวร์ |
| `general_other` | `general_ai` | คำถามหรืองานทั่วไปที่คลังเราไม่ครอบคลุม เช่น เขียนอีเมล แปลภาษา สรุปข้อความ คำนวณ สูตรอาหาร |
| `out_of_scope` | `decline` | **เฉพาะ**คำขอที่ผิดกฎหมายหรือทำร้ายผู้อื่น เช่น แฮกบัญชีคนอื่น ดักฟัง ปลอมเอกสาร — เรื่องที่แค่ไม่เกี่ยวกับ IT ไม่ใช่หมวดนี้ ให้ไป `general_other` |

**หกหมวดแรกจับคู่กับหมวดในคลังความรู้โดยตรง นี่คือหัวใจ** — ถ้าหมวดของ classifier ไม่ตรงกับสิ่งที่คลังตอบได้ คำถามจะถูกส่งไป `general_ai` แล้วไม่มีวันไปถึง retrieval โดยไม่มี error ให้เห็นเลย
ทุกหมวดที่ชี้ไป `university_rag` ถ้า retrieval คืน `chunks` ว่าง → router fallback เป็น `general_ai` พร้อมบอกผู้ใช้ว่าไม่ได้อ้างอิงเอกสาร

ใช้ตารางนี้เมื่อ `score ≥ 0.75` เท่านั้น ต่ำกว่านั้นให้ตกไปชั้น 3 (LLM)
ส่วน route `local_ai` **ไม่ได้มาจากตารางนี้** — มาจากชั้น rules เมื่อผู้ใช้ขอ "จำแนก/จัดประเภทคำร้อง" ตรง ๆ

## 4. router → retrieval
`POST /search`
```json
{ "request_id": "uuid", "query": "...", "top_k": 5, "filters": { "category": "it_support", "year_from": 2023 } }
```
```json
{
  "request_id": "uuid",
  "chunks": [
    { "chunk_id": "it-wifi-001#p3#c2", "text": "...", "score": 0.82, "bm25_score": 11.2, "vector_score": 0.77, "source": Source }
  ],
  "latency_ms": 350
}
```
`chunks` ว่าง = ไม่เจอ (ไม่ใช่ error)

## 5. router → generation
`POST /generate`
```json
{
  "request_id": "uuid",
  "mode": "grounded | passthrough | explain_local",
  "query": "...",
  "history": [ HistoryMessage ],
  "contexts": [ { "ref": 1, "text": "...", "source": Source } ],   // grounded
  "draft": "คำตอบจาก engine (passthrough / explain_local)"
}
```
```json
{
  "request_id": "uuid",
  "answer": "...",
  "sources": [ Source ],          // เฉพาะที่ถูกอ้างถึงจริงในคำตอบ
  "blocked": false, "block_reason": null,
  "model": "openai/gpt-oss-120b | none", "latency_ms": 1500, "token_usage": TokenUsage
}
```
- `grounded`: เรียก LLM สร้างคำตอบจาก contexts ต้องมี [n]
- `passthrough`: **ไม่เรียก LLM** ทำแค่ safety + format ของ draft
- `explain_local`: เรียก LLM สั้นๆ เปลี่ยนผล classifier เป็นประโยคคน

## 6. api → response-log
| Method | Path | Body / Query | Response |
|---|---|---|---|
| POST | `/log` | `LogEntry` | `202 {accepted:true}` |
| POST | `/feedback` | `{message_id, user_id, rating, comment?}` | `{ok:true}` |
| GET | `/sessions?user_id=` | – | `{sessions:[...]}` |
| GET | `/history/{session_id}?user_id=&limit=20` | – | `{session_id, messages:[Message]}` |
| GET | `/stats?days=7` | – | `Stats` |

**กติกาสี่ข้อของ 07 ที่ต้องทำเหมือนกันทุกที่ (ล็อกแล้ว — สี่ข้อนี้คือจุดที่ระบบพังเงียบตอนรวมงาน)**

1. **`limit` = จำนวนข้อความ *ล่าสุด*** ไม่ใช่ข้อความแรก — query คือ `ORDER BY created_at DESC LIMIT n` แล้ว **กลับลำดับก่อนตอบ** ให้ผลลัพธ์เรียง เก่า→ใหม่ เสมอ
   (ถ้าทำเป็น `ASC LIMIT 10` ตรง ๆ บทสนทนายาว ๆ จะส่งข้อความเก่าสุดไปให้ router → follow-up เพี้ยนโดยไม่มี error)
2. **`user_id` บังคับใส่ใน `/history/{session_id}`** — 07 ต้องเช็กว่า session เป็นของ user นั้นจริง ถ้าไม่ใช่ตอบ `404` (ไม่ใช่ 403 เพื่อไม่ให้เดาได้ว่ามี session นี้อยู่)
   api เป็นคนบอกว่า user เป็นใคร 07 เชื่อค่านี้ได้เพราะอยู่ใน network ภายใน **แต่ต้องเช็กความเป็นเจ้าของ** ไม่ใช่เชื่อทุกอย่าง
3. **session ที่ยังไม่มีข้อมูล → ตอบ `200` พร้อม `messages: []`** ห้ามตอบ 404
   เหตุผล: `/log` ถูกยิงแบบไม่รอ (async) ผู้ใช้อาจกด refresh ก่อน log ลง DB
4. **`/feedback` มาถึงก่อน `/log` ได้** (ผู้ใช้กด 👍 เร็วกว่า log ลง DB) — ห้ามใช้ FK แข็งที่ทำให้ insert ล้ม
   ให้เก็บ feedback ไว้ก่อนด้วย `message_id` ที่ยังไม่มีแถว แล้วค่อยเชื่อมเมื่อ `/log` มาถึง (upsert ด้วย `message_id` เป็น unique key) และตอบ `{ok:true}` ตามปกติ

```json
// LogEntry — api สร้าง session_id + message_id เองแล้วยิงแบบไม่รอ
// 07 เป็นคน "สร้างแถว conversation" ให้อัตโนมัติถ้ายังไม่มี (upsert จาก session_id ใน LogEntry)
// api ไม่ต้องเรียก endpoint สร้าง session แยก
{
  "request_id": "uuid", "session_id": "uuid", "user_id": "uuid",
  "user_message_id": "uuid", "assistant_message_id": "uuid",
  "user_message": "...", "answer": "...", "sources": [ Source ],
  "route": "...", "engines_used": [], "confidence": 0.9, "reasoning": "...",
  "latency_ms": 3900, "token_usage": TokenUsage, "status": "ok | error", "error_code": null,
  "created_at": "..."
}
// Stats
{
  "total_requests": 120, "avg_latency_ms": 3100, "p95_latency_ms": 7200,
  "by_route": { "university_rag": 70, "general_ai": 30 },
  "feedback": { "up": 40, "down": 6 }, "error_rate": 0.03,
  "top_downvoted": [ { "message_id": "...", "question": "..." } ]
}
```

## 7. Environment variables (ชื่อกลาง ห้ามตั้งชื่อเอง)
```
# common
LOG_LEVEL=INFO
TZ=Asia/Bangkok
# llm — Groq เป็นหลัก เจ้าอื่นเป็นตัวสำรอง
LLM_PRIMARY=groq            # groq | gemini | openai
LLM_FALLBACK=gemini         # ใช้เมื่อตัวหลัก timeout / 429 / ล่ม
GROQ_API_KEY=    GROQ_MODEL=openai/gpt-oss-120b
GEMINI_API_KEY=  GEMINI_MODEL=
OPENAI_API_KEY=  OPENAI_MODEL=
# urls (ภายใน docker network)
API_URL=http://api:8000
ROUTER_URL=http://router:8000
ENGINES_URL=http://engines:8000
RETRIEVAL_URL=http://retrieval:8000
GENERATION_URL=http://generation:8000
RESPONSE_LOG_URL=http://response-log:8000
# db
DATABASE_URL=postgresql+psycopg://dl06:dl06@postgres:5432/dl06
# api
JWT_SECRET_KEY=  JWT_EXPIRE_MINUTES=480  MAX_UPLOAD_MB=10
# retrieval
EMBEDDING_MODEL=intfloat/multilingual-e5-base  INDEX_DIR=/data/index  HF_HOME=/models
# generation
GENERATION_TEMPERATURE=0.3  MAX_OUTPUT_TOKENS=2048  MODERATION_ENABLED=true
```
(ค่าจริงของ model name ให้เจ้าของ service ยืนยันใน `.env.example` วัน D2)

### วิธีต่อ LLM ที่ทีมใช้ร่วมกัน — หนึ่งไลบรารี สลับเจ้าด้วย `base_url`

**ห้ามต่างคนต่างใช้ SDK คนละตัว** ทั้ง Groq, OpenAI และ Gemini มี endpoint ที่เข้ากันได้กับ OpenAI หมด
ใช้ไลบรารี `openai` ตัวเดียวแล้วเปลี่ยนแค่ `base_url` กับ key — วิธีนี้พิสูจน์แล้วว่าใช้ได้จริงในงาน RAG เดิมของทีม

| provider | `base_url` | ตัวแปร key |
|---|---|---|
| **groq** (หลัก) | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` |
| gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `GEMINI_API_KEY` |
| openai | `https://api.openai.com/v1` | `OPENAI_API_KEY` |

ใครที่ต้องเรียก LLM (03, 04, 06) เขียนฟังก์ชันสร้าง client แบบเดียวกัน อ่าน `LLM_PRIMARY` จาก env แล้วเลือกแถวในตารางนี้
สลับเจ้าได้โดยแก้ `.env` บรรทัดเดียว ไม่ต้องแก้โค้ด

**กับดักของ Groq ที่ทีมเคยโดนมาแล้วจริง ๆ — อ่านให้จบ**
1. **Groq ถอดโมเดลออกโดยไม่แจ้งล่วงหน้า** ทีมเคยใช้ `llama-3.3-70b-versatile` แล้วถูกถอดออก (เจอเมื่อ 18 ส.ค. 2026) ตัวที่ใช้อยู่ตอนนี้คือ `openai/gpt-oss-120b`
   → **อย่า hardcode ชื่อโมเดลในโค้ด** อ่านจาก `GROQ_MODEL` เสมอ และตอน startup ให้ยิงคำถามสั้น ๆ หนึ่งครั้งเช็กว่าโมเดลยังอยู่ ถ้าไม่อยู่ให้ขึ้น log เตือนชัด ๆ ไม่ใช่รอให้ล้มตอนมีผู้ใช้
2. **free tier จำกัดจำนวนคำขอต่อนาที** และเราแปดคน — **ตอน dev ทุกคนใช้ key ของตัวเอง** (สมัครฟรีที่ console ของ Groq) แล้วค่อยใช้ key กลางของทีมเฉพาะวันสาธิต
3. **Groq ไม่มีระบบ safety ฝั่งผู้ให้บริการแบบ Gemini** ไม่มี safety settings ให้ตั้งและไม่มีเหตุผลการบล็อกกลับมา → โมดูล 06 ต้องพึ่งการตรวจของตัวเองเป็นหลัก (กฎใน prompt + regex + ตรวจ `finish_reason`) ห้ามคิดว่าผู้ให้บริการกรองให้แล้ว
5. **`gpt-oss-120b` ใช้ token ไปกับการคิดก่อนตอบ และนับรวมใน `max_tokens`** (วัดจริง 19 ก.ย.) ค่า default คิดเยอะจนคำตอบ JSON ของ router เกิน 300 token แล้ว Groq ตอบ `400 json_validate_failed` และคำตอบ RAG โดนตัดที่ 1024 กลางประโยค
   → ทุกจุดที่เรียก Groq ให้ส่ง `extra_body={"reasoning_effort": "low"}` (ส่งเฉพาะตอน provider เป็น groq) วัดแล้ว route ยังถูกเท่าเดิม ใช้ token น้อยลง ~4 เท่าและเร็วขึ้น
   → `max_tokens` ของคำตอบ JSON สั้น ๆ ≥ 1024 · คำตอบยาวใช้ `MAX_OUTPUT_TOKENS` (2048) · เช็ก `finish_reason == "length"` แล้ว log ไว้ทุกครั้ง อย่าส่งคำตอบที่ขาดกลางประโยคโดยไม่รู้ตัว
6. **8,000 token/นาที ต่อ key** — คำถาม RAG หนึ่งข้อใช้ ~3,000–6,000 token (router + generation) แปลว่า key เดียวรับได้แค่ ~2 คำถามต่อนาที เกินแล้วได้ 429
   → ต้องมี `GEMINI_API_KEY` เป็นตัวสำรองวันสาธิต · ถ้าตัวสำรองไม่มี key ให้ข้ามไปเลย อย่ายิงแล้วได้ 400 ซ้อนอีกชั้น
7. **ข้อดีที่ควรใช้ประโยชน์**: Groq เร็วกว่าเจ้าอื่นมาก คอขวดของเราจะเป็น rate limit ไม่ใช่ความเร็ว → งบเวลา 70 วินาทีของ router จะเหลือเฟือ เอาเวลาที่ประหยัดได้ไปทำ reranking หรือ citation check เพิ่มได้

## Changelog
- **v1.6 (19 ก.ย. 2026)** — §7 กับดักของ Groq เพิ่มข้อ 5–6 จากการวัดด้วย key จริง (gpt-oss คิดกิน `max_tokens` → ส่ง `reasoning_effort=low` · 8,000 token/นาที → ต้องมีตัวสำรอง) · `MAX_OUTPUT_TOKENS` 1024 → 2048 ไม่มี field ไหนเปลี่ยน
- **v1.5 (19 ก.ย. 2026)** — §3 เขียนความหมายของ `general_other` / `out_of_scope` ให้ชัด ไม่เปลี่ยนชื่อหมวดหรือตาราง map
  - คำว่า "นอกขอบเขต" ของเดิมทำให้งานทั่วไป (เขียนอีเมล แปลภาษา) ถูกติดป้าย `out_of_scope` แล้วโดนปฏิเสธ ทั้งที่ golden set กำหนดให้เป็น `general_ai`
- **v1.4 (D1)** — **เปลี่ยน LLM หลักเป็น Groq** (Gemini/OpenAI ยังเป็นตัวสำรองเหมือนเดิม)
  - §7 เพิ่ม `GROQ_API_KEY` / `GROQ_MODEL` / `LLM_FALLBACK` · `LLM_PRIMARY=groq`
  - เพิ่มตาราง `base_url` ของทั้งสามเจ้า + กติกาว่าใช้ไลบรารี `openai` ตัวเดียวทั้งทีม
  - เขียนกับดักของ Groq 4 ข้อ (ถอดโมเดลเงียบ, rate limit, ไม่มี safety ฝั่งผู้ให้บริการ, เร็วกว่ามาก)
  - ตัวอย่าง `model` ในทุก response เปลี่ยนเป็นชื่อโมเดลจริงของ Groq
- **v1.3 (D1, หลังอาจารย์ยืนยันว่าปรับได้ทั้งหมด)**
  - **โดเมนปลดล็อกแล้ว** (อาจารย์ยืนยัน "ไม่จำเป็น ปรับได้ทั้งหมด") ตัวอย่างข้อมูลทั้งหมดเปลี่ยนจากเอกสารมหาวิทยาลัยเป็นคลังความรู้จริงที่เราใช้
  - §3 **เปลี่ยนหมวด classifier ทั้ง 8 หมวดให้ตรงกับหมวดในคลังความรู้จริง** ของเดิมเป็นหมวดฝ่ายทะเบียนซึ่งไม่ตรงกับคลังเลย
  - `category` ของเอกสารเปลี่ยนเป็น `it_support` / `howto` / `faq` / `policy` / `other`
  - คง enum `university_rag` ไว้ตามผังอาจารย์ แต่บังคับว่าหน้าเว็บต้องแปลงเป็นป้ายภาษาคน
  - เพิ่ม object `Trace` (optional) ใน `RouteResponse` และ `ChatResponse` เพื่อให้หน้าเว็บโชว์ได้ว่า agent ตัดสินใจที่ชั้นไหนและใช้เวลาตรงไหน
- **v1.2 (D1)** — เพิ่ม `it_support` ใน category ของเอกสาร (คลัง IT helpdesk ที่นำกลับมาใช้ ดู `05_retrieval_knowledge.md`) ไม่กระทบ field อื่น
- **v1.1 (D1, 16 ก.ย. 2026)** — ปิดช่องที่จะพังตอนรวมงาน ไม่มีการลบ/เปลี่ยนชื่อ field เดิม
  - §0 เพิ่มงบเวลารวมของ router (70s) และนิยาม `confidence`
  - §1 `/api/stats` รับ `days`, กำหนดวิธีรวมหลายไฟล์เป็น `file_text`
  - §2 ระบุว่า `history` คือ 10 ข้อความล่าสุดแต่เรียงเก่า→ใหม่
  - §3 เพิ่มตาราง map หมวด classifier → route (เดิมไม่มี ทำให้ 03 กับ 04 ตกลงกันไม่ได้)
  - §6 `/history` ต้องมี `user_id`, กติกา 4 ข้อเรื่อง limit / ownership / session ว่าง / feedback มาก่อน log
- v1 (D1) — ฉบับแรก
