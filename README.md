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

| โมดูล | ผู้รับผิดชอบ | โฟลเดอร์ | ผลที่วัดได้ |
|---|---|---|---|
| 01 Web App | | `services/01_web_app/` | |
| 02 API Backend | | `services/02_api_backend/` | |
| 03 AI Router | | `services/03_ai_router_agent/` | |
| 04 AI Engines | | `services/04_ai_model_selection/` | |
| 05 Retrieval | | `services/05_retrieval_knowledge/` | |
| 06 LLM Generation | | `services/06_llm_generation/` | |
| 07 Response / Log | | `services/07_response_logging/` | |
| 08 Docker / Integration | Pitchakorn Phuadkhunthod | `08_monitoring_deployment/` + root | |

## เริ่มยังไง

```bash
cp .env.example .env     # แล้วใส่ API key
make up                  # ขึ้นทั้งระบบ
make warmup              # ดึงโมเดลลง volume ครั้งแรก
make ingest              # สร้างดัชนีค้นหา
make smoke               # ทดสอบว่าต่อกันติดทั้งเส้น
```

เปิด http://localhost:3000

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
