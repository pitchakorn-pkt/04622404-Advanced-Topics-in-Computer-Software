# ช่วยด้วย (ChuayDuay)

ผู้ช่วยตอบคำถามภาษาไทยเรื่องปัญหาการใช้งานมือถือและคอมพิวเตอร์ ตอบจากคลังความรู้ของระบบเองพร้อมแหล่งอ้างอิงที่ตรวจสอบได้

เป็นระบบ **agentic RAG** ที่แยกเป็น 8 โมดูล รันด้วย Docker Compose คำสั่งเดียว
งานรายวิชา **04622404 Advanced Topics in Computer Software — DL-06 Agentic AI System I**

## ระบบทำงานยังไง

```
เบราว์เซอร์ → web → api → router ─┬─ university_rag → retrieval → generation (grounded)
                                   ├─ general_ai     → engines   → generation (passthrough)
                                   ├─ local_ai       → engines   → generation (explain_local)
                                   ├─ clarify        → ตอบกลับด้วย template
                                   └─ decline        → ปฏิเสธอย่างสุภาพ
                                            ↓
                                     response-log → postgres
```

`router` เป็นคนตัดสินใจว่าคำถามควรไปทางไหน โดยไล่เป็นชั้น — กฎ keyword ก่อน แล้วค่อยโมเดลจำแนกในเครื่อง
และเรียก LLM เฉพาะตอนที่ยังไม่มั่นใจ เพื่อให้เร็วและไม่เปลืองโควตา

## สมาชิกและความรับผิดชอบ

| โมดูล | ผู้รับผิดชอบ | branch | ผลที่วัดได้ |
|---|---|---|---|
| [01 Web App](services/01_web_app/) | [@jakkrich0912-web](https://github.com/jakkrich0912-web) | `feature/01-web-jakkrich0912-web` | |
| [02 API Backend](services/02_api_backend/) | [@Chakamon02](https://github.com/Chakamon02) | `feature/02-api-Chakamon02` | |
| [03 AI Router](services/03_ai_router_agent/) | [@Patcharanat23](https://github.com/Patcharanat23) | `feature/03-router-Patcharanat23` | |
| [04 AI Engines](services/04_ai_model_selection/) | [@pathumpornjorrapong-ops](https://github.com/pathumpornjorrapong-ops) | `feature/04-engines-pathumpornjorrapong-ops` | |
| [05 Retrieval](services/05_retrieval_knowledge/) | [@SoSick41](https://github.com/SoSick41) | `feature/05-retrieval-SoSick41` | |
| [06 LLM Generation](services/06_llm_generation/) | [@phitphibul67](https://github.com/phitphibul67) | `feature/06-generation-phitphibul67` | |
| [07 Response / Log](services/07_response_logging/) | [@jirapa-gm](https://github.com/jirapa-gm) | `feature/07-responselog-jirapa-gm` | |
| [08 Docker / Integration](08_monitoring_deployment/) | [@pitchakorn-pkt](https://github.com/pitchakorn-pkt) | `main` / `develop` | |

ช่อง "ผลที่วัดได้" เจ้าของแต่ละโมดูลเติมเองตอนมีตัวเลขจริง เช่น route accuracy, hit@5, % คำตอบที่มีอ้างอิง

## เริ่มยังไง

```bash
cp .env.example .env     # แล้วใส่ API key
make up                  # ขึ้นทั้งระบบ รอจนทุกตัว healthy
make warmup              # ดึงโมเดลลง volume — ครั้งแรกบนเครื่องใหม่ต้องทำ
make ingest              # สร้างดัชนีค้นหา
make smoke               # ทดสอบว่าต่อกันติดทั้งเส้น
```

เปิด http://localhost:3000 · ผู้ใช้ตัวอย่าง `student` / `student`

### ถ้าเครื่องไม่มี `make`

Windows ส่วนใหญ่ไม่มีมาให้ และ macOS บางเครื่องต้องยอมรับ license ของ Xcode ก่อน
(`sudo xcodebuild -license` แล้วกด space ลงไปจนสุด พิมพ์ `agree`) — ใช้คำสั่งเต็มแทนได้ ผลเหมือนกันทุกอย่าง

| แทน | ใช้ |
|---|---|
| `make up` | `docker compose up -d --wait` |
| `make down` | `docker compose down` |
| `make build` | `docker compose build` |
| `make ps` | `docker compose ps` |
| `make logs s=router` | `docker compose logs -f --tail=100 router` |
| `make rebuild s=router` | `docker compose build --no-cache router && docker compose up -d router` |
| `make smoke` | `bash scripts/smoke_test.sh` |
| `make ingest` | `docker compose run --rm retrieval python ingest.py` |
| `make eval` | `python3 scripts/eval_e2e.py` |

### ตอนนี้ยังเป็นโครงเปล่า

ทุก service ตอบค่าปลอมที่หน้าตาถูกตาม `docs/CONTRACT.md` แต่ **ทั้งเส้นวิ่งได้จริงแล้ว**
`web → api → router → engines / retrieval / generation → response-log` ต่อกันผ่าน HTTP จริง
เจ้าของแต่ละโมดูลมาแทนคำว่า `STUB: replace` ในโฟลเดอร์ของตัวเองด้วยของจริง

## เอกสาร

| ไฟล์ | อ่านเมื่อไหร่ |
|---|---|
| [`docs/00_PLAN_OVERVIEW.md`](docs/00_PLAN_OVERVIEW.md) | อ่านก่อนอย่างอื่น — ภาพรวม สถาปัตยกรรม ข้อตกลงของทีม |
| [`docs/CONTRACT.md`](docs/CONTRACT.md) | **กฎสูงสุด** รูปแบบ JSON ทุกเส้น ชื่อ env ทุกตัว — โค้ดขัดกับมันเมื่อไหร่ถือว่าโค้ดผิด |
| [`docs/SCHEDULE.md`](docs/SCHEDULE.md) | ใครต้องส่งอะไรวันไหน ใครรอใครอยู่ |
| [`docs/GIT_FLOW.md`](docs/GIT_FLOW.md) | วิธีใช้ git ของทีม ทำตามทีละขั้น |

## กติกาการส่งงาน

- คนละหนึ่งโฟลเดอร์ คนละหนึ่ง branch — แก้ได้เฉพาะโฟลเดอร์ของตัวเอง
- เข้า `develop` ผ่าน Pull Request เท่านั้น **ห้าม push ตรง**
- `main` รับ merge จาก `develop` อย่างเดียว
- เจอบั๊กในงานคนอื่น → เปิด Issue แท็กเจ้าของ **ห้ามแก้เอง**
- แก้ `docs/CONTRACT.md` ต้องผ่าน PR แยกและได้ approve จากคนที่เกี่ยวข้อง

รายละเอียดทั้งหมดอยู่ใน [`docs/GIT_FLOW.md`](docs/GIT_FLOW.md)
