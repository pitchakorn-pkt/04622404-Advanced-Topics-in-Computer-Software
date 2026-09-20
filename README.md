# ช่วยด้วย (ChuayDuay)

**ผู้ช่วยตอบคำถามภาษาไทยเรื่องปัญหาการใช้งานมือถือและคอมพิวเตอร์** ตอบจากคลังความรู้ของระบบเองพร้อมแหล่งอ้างอิงที่ตรวจสอบได้

เป็นระบบ **agentic RAG** แยกเป็น 8 โมดูลที่คุยกันผ่าน HTTP รันทั้งระบบด้วย Docker Compose คำสั่งเดียว
งานรายวิชา **04622404 Advanced Topics in Computer Software — DL-06 Agentic AI System I**

---

## ทีม

8 คน · 1 คนต่อ 1 โมดูล · หัวหน้าทีมดูแลโมดูล 08 และรวมงานทุกโมดูลเข้าด้วยกัน

| โมดูล | ชื่อ–สกุล | รหัสนักศึกษา | GitHub |
|---|---|---|---|
| [01 Web App](services/01_web_app/) | Jakkrich Sriraksa | 116730462014-5 | [@jakkrich0912-web](https://github.com/jakkrich0912-web) |
| [02 API Backend](services/02_api_backend/) | Karmolputh Phatarathorn | 116610462034-7 | [@Chakamon02](https://github.com/Chakamon02) |
| [03 AI Router](services/03_ai_router_agent/) | Patcharanat Budploy | 116730462038-4 | [@Patcharanat23](https://github.com/Patcharanat23) |
| [04 AI Engines](services/04_ai_model_selection/) | Pathumporn Jorrapong | 116730462009-5 | [@pathumpornjorrapong-ops](https://github.com/pathumpornjorrapong-ops) |
| [05 Retrieval](services/05_retrieval_knowledge/) | Suphakorn Nonthong | 116730462028-5 | [@SoSick41](https://github.com/SoSick41) |
| [06 LLM Generation](services/06_llm_generation/) | Phitphibul Phrompheak | 116730462030-1 | [@phitphibul67](https://github.com/phitphibul67) |
| [07 Response / Log](services/07_response_logging/) | Jirapa Gongmool | 116730462008-7 | [@jirapa-gm](https://github.com/jirapa-gm) |
| [08 Docker / Integration](08_monitoring_deployment/) | Pitchakorn Phuadkhunthod **(หัวหน้าทีม)** | 116730462035-0 | [@pitchakorn-pkt](https://github.com/pitchakorn-pkt) |

| โมดูล | รับผิดชอบอะไร |
|---|---|
| **01 Web App** | หน้าเว็บที่ผู้ใช้เห็น — แชท แหล่งอ้างอิงใต้คำตอบ ประวัติแชท แผงแสดงการตัดสินใจของ agent การ์ดสถิติ ปุ่มคัดลอกคำตอบ |
| **02 API Backend** | ประตูหน้าบ้าน — ล็อกอิน ตรวจ input ประกอบ context จำกัดอัตราการถาม แล้วส่งต่อให้ router |
| **03 AI Router** | สมองของระบบ — ตัดสินใจว่าคำถามไป route ไหน ด้วย 4 ชั้น guard → rules → classifier → LLM |
| **04 AI Engines** | General AI ผ่าน Groq พร้อมตัวสำรอง · Local AI โมเดลจำแนก 8 หมวดที่เทรนเอง |
| **05 Retrieval** | เตรียมคลังความรู้และค้นแบบ hybrid BM25 + vector — ที่มาของแหล่งอ้างอิงทุกข้อ |
| **06 LLM Generation** | เขียนคำตอบพร้อมเลขอ้างอิงที่ตรวจแล้ว · ด่านความปลอดภัยและปิดข้อมูลส่วนตัว |
| **07 Response / Log** | ความจำของระบบ — เก็บบทสนทนา feedback สรุปสถิติ และ export feedback เป็น CSV |
| **08 Docker / Integration** | รวม 7 โมดูลให้รันด้วยคำสั่งเดียว · Docker · smoke test และวัดผลทั้งระบบ · รีวิว PR |

---

## ผลที่วัดได้

ทุกตัวเลขในหัวข้อนี้มาจากการรันจริงบนเครื่อง ไม่มีค่าที่พิมพ์เอง — รันซ้ำได้ด้วย `make smoke` และ `make eval`

**ทั้งระบบ — ชุดทดสอบ 64 คำถาม ยิงผ่าน `/api/chat` เหมือนผู้ใช้จริง**

| ตัวชี้วัด | ค่า |
|---|---|
| เลือกเส้นทางถูก (route accuracy) | **85.9%** · 55/64 |
| คำตอบสาย RAG ที่มีแหล่งอ้างอิงจริง | **51/60** |
| เวลาตอบเฉลี่ย | **2.2 วินาที** |
| เวลาตอบ p95 | **3.7 วินาที** |
| คำขอที่ล้มเหลว | **0** |

**การค้นคลังความรู้ — วัดกับ golden set ที่มีเฉลย**

| วิธีค้น | hit@1 | hit@5 | MRR |
|---|---|---|---|
| BM25 อย่างเดียว | 0.4000 | 0.6500 | 0.4794 |
| vector อย่างเดียว | 0.5000 | 0.8500 | 0.6325 |
| **hybrid (RRF) — ที่ระบบใช้จริง** | **0.4667** | **0.8500** | **0.6011** |
| hybrid + cross-encoder rerank | 0.7167 | 0.9333 | 0.7978 |

**ชุดทดสอบอัตโนมัติ**

| ชุด | ผล |
|---|---|
| `make smoke` — ทั้งเส้นครบ 5 route + ประวัติ + สถิติ | **14/14** |
| unit test ของ 03 AI Router | **87 ผ่าน** |
| unit test ของ 02 API Backend | **31 ผ่าน** |
| โมเดลจำแนกหมวดของ 04 (cross-validation) | **82.07%** |

<sub>ชุด 64 คำถามรันด้วย `gemini-3.5-flash-lite` เว้นระยะ 10 วินาทีต่อข้อ เพื่อกันโควตารายวันของ Groq ไว้ใช้วันนำเสนอ · cross-encoder rerank วัดแล้วดีขึ้นจริงแต่ปิดไว้เป็นค่าเริ่มต้น เหตุผลอยู่ในหัวข้อ "ข้อจำกัดที่รู้อยู่"</sub>

<sub>**อ่านเลข route accuracy ต้องรู้ด้วยว่าชุดทดสอบเอียง** — 64 ข้อนั้นเป็น `university_rag` 60 ข้อ ที่เหลือ `general_ai` / `local_ai` / `clarify` / `decline` หมวดละ 1 ข้อ ตั้งใจถ่วงไปทางคลังความรู้เพราะเป็นเส้นทางหลักที่ต้องมีแหล่งอ้างอิง ผลคือตัวเลขนี้เทียบกับ benchmark ที่แบ่งหมวดเท่ากันไม่ได้ และตัวตัดสินใจที่ตอบ `university_rag` ทุกข้อโดยไม่คิดเลยจะได้ 60/64 บนชุดนี้ · ส่วน "คำตอบสาย RAG ที่มีแหล่งอ้างอิงจริง" นับจาก 60 ข้อนั้นโดยตรง จึงไม่ได้รับผลจากความเอียง</sub>

---

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

`router` เป็นคนเดียวที่ตัดสินใจ และตัดสินใจเป็นชั้น หยุดทันทีเมื่อมั่นใจพอ

| ชั้น | ทำอะไร | เรียก LLM ไหม |
|---|---|---|
| 0 guard | ข้อความว่าง สั้นเกิน อ้างอิงลอย ๆ → `clarify` · คำขอที่ไม่ควรตอบ → `decline` | ไม่ |
| 1 rules | คำสำคัญของโดเมน (ไวไฟ รหัสผ่าน แบต เครื่องช้า …) → `university_rag` | ไม่ |
| 2 classifier | โมเดลจำแนก 8 หมวดที่เทรนเอง รันในเครื่อง ใช้เมื่อมั่นใจ ≥ 0.75 | ไม่ |
| 3 LLM | เหลือเฉพาะที่ยังไม่มั่นใจ ขอคำตอบเป็น JSON | ใช่ |

ทำแบบนี้เพราะการส่งทุกคำถามให้ LLM จำแนกทั้งช้าและเปลืองโควตาที่แชร์กันทั้งทีม
`router` บันทึกทุกครั้งว่าจบที่ชั้นไหนแล้วคืนกลับมาใน `trace` จึงวัดได้ว่ากี่เปอร์เซ็นต์ไม่ต้องเรียก LLM เลย

**สิ่งที่ระบบทำได้ตอนนี้** — ล็อกอิน · ถาม-ตอบต่อเนื่องจำบริบทเดิมได้ · แสดงแหล่งอ้างอิงใต้คำตอบ · ประวัติแชทย้อนหลัง · กางดูการตัดสินใจของ agent · คัดลอกคำตอบ · การ์ดสถิติการใช้งาน · ปิดข้อมูลส่วนตัวในคำตอบอัตโนมัติ · สลับผู้ให้บริการ LLM เองเมื่อเจ้าหลักล่มหรือโควตาหมด

---

## เริ่มยังไง

```bash
git clone https://github.com/pitchakorn-pkt/chuayduay.git
cd chuayduay
cp .env.example .env     # แล้วใส่ API key ของตัวเอง
make up                  # ขึ้นทั้งระบบ รอจนทุกตัว healthy
make smoke               # ทดสอบว่าต่อกันติดทั้งเส้น
```

ครั้งแรกบนเครื่องใหม่ต้องเตรียมคลังความรู้ก่อนด้วย

```bash
make warmup              # ดึงโมเดล embedding ลง volume
make ingest              # สร้างดัชนีค้นหาจากเอกสาร
```

> [!IMPORTANT]
> **รัน `make ingest` ตอนที่ระบบขึ้นอยู่แล้ว ต้อง `docker compose restart retrieval` ตามทุกครั้ง**
> เพราะ ingest เขียนดัชนีชุดใหม่ แต่ service ที่รันค้างอยู่ยังถือดัชนีชุดเดิมที่ถูกเขียนทับไปแล้ว
> อาการจะหลอกมาก: ระบบไม่ล่ม ผู้ใช้ยังได้คำตอบ (router ถอยไปตอบด้วยความรู้ทั่วไป) **แต่แหล่งอ้างอิงจะหายไปเงียบ ๆ**

ถ้า `make warmup` / `make ingest` ขึ้น `PermissionError: /models/...` หรือ `/data/index` แปลว่า volume ในเครื่องถูกสร้างไว้ตั้งแต่ก่อนแก้ Dockerfile และยังเป็นของ root อยู่ แก้ครั้งเดียวด้วย

```bash
docker compose run --rm -u root retrieval chown -R 10001:10001 /data/index /models
```

---

## การตัดสินใจเชิงออกแบบ

เขียนไว้เพื่อให้อธิบายได้ตอนนำเสนอ และเพื่อไม่ให้มีใครไปแก้กลับโดยไม่รู้เหตุผล

**Retrieval ทำงานเฉพาะ route `university_rag`** ไม่ใช่ทุกคำถาม
ในแผนภาพต้นแบบทุกเส้นวิ่งผ่าน Retrieval แต่คำถามทั่วไปไม่ควรต้องไปค้นคลังความรู้ก่อน — เสียเวลาฟรีและได้ context ที่ไม่เกี่ยวมาปน · `clarify` กับ `decline` ไม่เรียก service ไหนเลย

**`generation` มีโหมด `passthrough` ที่ไม่เรียก LLM**
ถ้าไม่มีโหมดนี้ คำถามเดียวจะเรียก LLM สองรอบ (ที่ `engines` และที่ `generation`) ช้าขึ้นเท่าตัวและกินโควตาที่แชร์กันทั้งทีม · ตรวจได้จาก `model: "none"` ในคำตอบ

**เส้น `university_rag` ห้ามจบด้วยการบอกผู้ใช้ว่าไม่มีข้อมูล**
ถ้าค้นไม่เจอ หรือเจอแต่เรียบเรียงคำตอบไม่ได้ ระบบจะถอยไปตอบด้วยความรู้ทั่วไปแล้วบอกตรง ๆ ว่าคำตอบนี้ไม่ได้อ้างอิงเอกสาร — ดีกว่าปล่อยให้ผู้ใช้ได้ข้อความว่า "ไม่พบข้อมูล" แล้วจบ

**ชื่อ route คง `university_rag` ไว้ตามผังต้นแบบ แต่หน้าเว็บห้ามโชว์ค่าดิบ**
ความหมายจริงคือ "เส้นทางที่ตอบจากคลังความรู้ที่เราดูแลเอง พร้อมอ้างอิง" หน้าเว็บแปลงเป็นป้ายภาษาคนก่อนแสดงเสมอ

**LLM หลักคือ Groq มี Gemini เป็นตัวสำรองที่สลับให้เองอัตโนมัติ** เมื่อเจ้าหลักล่มหรือโควตาหมด
ตาราง provider มี OpenAI อยู่ด้วย แต่ระบบวนลองทีละคู่ตาม `LLM_PRIMARY` → `LLM_FALLBACK` เท่านั้น ไม่ได้ไล่ครบทั้งสามเจ้า
ทุกเจ้าเรียกผ่านไลบรารี `openai` ตัวเดียวกัน สลับด้วย `base_url` อย่างเดียว — เปลี่ยนผู้ให้บริการได้ด้วยการแก้ `.env` บรรทัดเดียว ไม่ต้องแตะโค้ด
**อย่า hardcode ชื่อโมเดล** อ่านจาก `GROQ_MODEL` เสมอ เพราะผู้ให้บริการถอดโมเดลออกโดยไม่แจ้งล่วงหน้าได้

**เนื้อหาจากไฟล์ที่ผู้ใช้แนบมาเป็น "ข้อมูล" ไม่ใช่ "คำสั่ง"**
วางเนื้อไฟล์ไว้ก่อนแล้วปิดท้ายด้วยคำสั่งจริงของผู้ใช้เสมอ พร้อมตัด role marker ปลอมออก — วัดแล้วว่าการเรียงกลับด้านทำให้คำสั่งที่ซ่อนในไฟล์ยึดคำตอบได้จริง

**ทุก request มี `X-Request-ID` ส่งต่อทุก hop และทุก service log เป็น JSON บรรทัดเดียว**
เวลารวมงานแล้วพัง ไล่ `request_id` เดียวกันผ่าน `make logs` จะรู้ทันทีว่าไปตายที่ hop ไหน

**`router` คืน `trace` กลับมาด้วย** บอกว่าตัดสินใจที่ชั้นไหนและใช้เวลาตรงไหนบ้าง
ข้อมูลนี้ไหลผ่านอยู่แล้วจึงไม่มีต้นทุนเพิ่ม แต่เก็บย้อนหลังไม่ได้ถ้าไม่ใส่ตั้งแต่แรก

**โมเดลกับดัชนีอยู่ใน named volume ไม่ใช่ใน image**
ไม่งั้น `build` ทุกครั้งจะโหลดใหม่เป็น GB และ image จะบวมจนแชร์กันไม่ไหว

**ล็อกอินใช้ผู้ใช้ตัวอย่างในฐานข้อมูล ตั้งใจไม่ทำหน้าสมัครสมาชิก**
โจทย์ของงานนี้คือตัวระบบ agentic ไม่ใช่ระบบสมาชิก · ตาราง `users` กับเส้นล็อกอิน–คุกกี้–เพดานคำถามรายบัญชีทำไว้ครบแล้ว เติมหน้าสมัครทีหลังได้โดยไม่ต้องรื้อของเดิม

---

## ข้อจำกัดที่รู้อยู่

ทุกข้อในตารางนี้รู้ตัวตั้งแต่ตอนทำ วัดหรือไล่โค้ดยืนยันแล้ว และรู้ว่าต้องแก้ตรงไหนถ้ามีเวลาต่อ

| เรื่อง | สภาพตอนนี้ | ถ้าจะทำต่อ |
|---|---|---|
| cross-encoder reranker | ปิดเป็นค่าเริ่มต้น วัดแล้วได้ hit@5 0.93 แต่กิน RAM รวม ~4.3 GB และเพิ่มเวลา ~15 วินาทีต่อคำถามบน CPU ล้วน | เปิดเมื่อมี GPU หรือย้ายไป reranker ตัวเล็กกว่า |
| คำถามหมวด "เลือกซื้ออุปกรณ์ / งานเอกสาร" | ไปเส้น `general_ai` ทั้งที่คลังมีคำตอบ ตอบถูกแต่ไม่มีเลขอ้างอิง — เป็นผลจากการ map หมวดใน CONTRACT ให้ผังอ่านง่าย | แยกหมวดพวกนี้กลับไป `university_rag` แล้ววัดใหม่ |
| แผงการตัดสินใจของ agent | กางดูได้เฉพาะแชทรอบปัจจุบัน แชทเก่ากดไม่ได้ ทั้งที่ฐานข้อมูลเก็บ `trace` ไว้ครบแล้ว | ให้ `/api/history` ส่งฟิลด์ `trace` กลับมาด้วย (แก้ ~3 บรรทัดที่ 07 และ 1 บรรทัดที่ 01) |
| ปุ่มให้คะแนนคำตอบ | ฝั่งหลังบ้านพร้อมหมด (`/api/feedback` · ตาราง `feedback` · export CSV) แต่หน้าเว็บชุดใหม่ยังไม่มีปุ่มให้กด | เติมปุ่มในหน้าแชทแล้วยิง `/api/feedback` ที่มีอยู่แล้ว |
| อัปโหลดไฟล์ | `/api/upload` ยังเป็น stub คืน 501 และหน้าเว็บยังไม่มีปุ่มแนบไฟล์ · ของที่ทำรอไว้แล้วคือตาราง `uploaded_files` และด่านกันคำสั่งแฝงใน `engines` ซึ่งยังไม่มีไฟล์จริงให้ทำงานด้วย | ต่อ pipeline อ่านไฟล์ → เก็บข้อความ → ส่งเป็น context |
| โควตา LLM | Groq free tier จำกัดทั้งต่อนาทีและต่อวัน ถ้าใช้หนักจะถอยไปตัวสำรองเอง | ใช้ key แบบเสียเงิน หรือรัน LLM ในเครื่อง |

---

## ทดสอบและวัดผล

```bash
make smoke     # ยิง /health ทุกตัว แล้วถาม 5 คำถามให้ครบทั้ง 5 route + ประวัติ + สถิติ
make eval      # รันชุดทดสอบ 64 ข้อผ่าน /api/chat จริง แล้วเขียนรายงาน
```

`make eval` เขียนออกมาสองไฟล์ — `eval/report.md` และ **`eval/report.html`** ซึ่งเป็นหน้าเว็บไฟล์เดียวจบ
เปิดด้วยการดับเบิลคลิกได้โดยไม่ต้องต่อเน็ต เอาไปเปิดโชว์ตอนนำเสนอหรือแคปใส่สไลด์ได้เลย
**ตัวเลขทุกตัวมาจากการรันจริง ไม่มีค่าที่พิมพ์เอง** และทั้งสองไฟล์อยู่ใน `.gitignore` เพราะเป็นผลรัน ไม่ใช่โค้ด

`smoke_test.sh` ตรวจ 14 ข้อ — `/health` ของ 6 service, ล็อกอิน, 5 คำถามให้ครบทั้ง 5 route, ประวัติ และสถิติ เป็นการดูว่าทั้งเส้นต่อกันติด ไม่ใช่ชุดทดสอบเคสขอบ
เคสที่เคยพังเงียบในระบบแบบนี้อยู่ใน pytest ของ 02 แทน — ขอประวัติ session ของคนอื่นต้องได้ 404 และบทสนทนายาวต้องส่งเข้า router แค่ 10 ข้อความล่าสุด · ส่วนการกด feedback ก่อนข้อความลงฐานข้อมูลทัน 07 รับไว้ด้วย upsert แล้วค่อยเชื่อมกันตอนอ่าน (ยังไม่มีเทสอัตโนมัติครอบเคสนี้)

ชุด 64 ข้อยิงด้วยบัญชีเดียว จึงชนเพดานจำนวนคำถามต่อนาทีของ `api` ได้ — สคริปต์รอตามที่ระบบบอกแล้วยิงซ้ำให้เอง ไม่นับเป็นข้อที่ตก
ถ้าอยากกันโควตารายวันของ Groq ไว้ ให้ตั้ง `LLM_PRIMARY=gemini` ก่อนรัน แล้วสลับกลับเมื่อเสร็จ

---

## คู่มือนักพัฒนา

<details>
<summary><b>ทำส่วนของตัวเอง — ไม่ต้องรอใคร ไม่ต้องทำ mock เอง</b></summary>

ทุกโมดูลตอบตาม `docs/CONTRACT.md` อยู่แล้ว คุณแก้แค่โฟลเดอร์ของตัวเอง ส่วนของเพื่อนที่คุณต้องเรียกจะตอบได้เสมอ งานของใครเสร็จช้าก็ไม่ทำให้คุณติด

```bash
git checkout develop && git pull
git checkout -b feature/<เลขโมดูล>-<ชื่อโมดูล>-<github username>
docker compose up -d --wait                    # ขึ้นทั้งระบบ
# แก้โค้ดใน services/<โฟลเดอร์ของคุณ>/app/ → reload ให้เองภายในไม่กี่วินาที ไม่ต้อง build ใหม่
curl localhost:<port ของคุณ>/health            # ยิงทดสอบ service ตัวเองตรง ๆ
docker compose logs -f <service ของคุณ>        # ดู error
```

| โมดูล | service | ยิงทดสอบที่ |
|---|---|---|
| 01 web | `web` | http://localhost:3000 (หรือ `npm run dev` ดู README ของ 01) |
| 02 api | `api` | `localhost:8000` |
| 03 router | `router` | `localhost:8003` |
| 04 engines | `engines` | `localhost:8004` |
| 05 retrieval | `retrieval` | `localhost:8005` |
| 06 generation | `generation` | `localhost:8006` |
| 07 response-log | `response-log` | `localhost:8007` |

**ต้อง build ใหม่เมื่อไหร่** — reload อัตโนมัติดูแค่ไฟล์ใน `app/`
ถ้าแก้ `requirements.txt`, `Dockerfile` หรือไฟล์นอก `app/` (เช่น `ingest.py`, `prompts/`) ให้สั่ง `docker compose up -d --build <service>`
ส่วน `web` build ใหม่ทุกครั้งที่แก้ ถ้าจะแก้บ่อยให้ใช้ `npm run dev`

**ห้ามแก้โฟลเดอร์ของคนอื่น** ถ้าอยากให้เพื่อนตอบอะไรเพิ่ม ให้ทักห้องเขาหรือ `#contract-changes`

</details>

<details>
<summary><b>ถ้าเครื่องไม่มี <code>make</code></b></summary>

Windows ส่วนใหญ่ไม่มีมาให้ และ macOS บางเครื่องต้องยอมรับ license ของ Xcode ก่อน
(`sudo xcode-select --switch /Library/Developer/CommandLineTools` แก้ได้เร็วที่สุด) — ใช้คำสั่งเต็มแทนได้ ผลเหมือนกันทุกอย่าง

| แทน | ใช้ |
|---|---|
| `make up` | `docker compose up -d --wait` |
| `make down` | `docker compose down` |
| `make build` | `docker compose build` |
| `make ps` | `docker compose ps` |
| `make logs s=router` | `docker compose logs -f --tail=100 router` |
| `make rebuild s=router` | `docker compose build --no-cache router && docker compose up -d router` |
| `make smoke` | `bash scripts/smoke_test.sh` |
| `make warmup` | `docker compose run --rm retrieval python -c "import os; from huggingface_hub import snapshot_download; snapshot_download(os.environ['EMBEDDING_MODEL'])"` |
| `make ingest` | `docker compose run --rm retrieval python ingest.py` |
| `make eval` | `python3 scripts/eval_e2e.py` |

</details>

<details>
<summary><b>ถ้าใช้ Windows</b></summary>

| เรื่อง | ทำแบบนี้ |
|---|---|
| ที่ clone repo | ไว้ที่ `C:\dev\chuayduay` **อย่าไว้ใน OneDrive หรือโฟลเดอร์ที่มีเว้นวรรค** — OneDrive ล็อกไฟล์ตอน sync และ docker mount โฟลเดอร์พวกนั้นแล้วพัง |
| รัน `.sh` | ใช้ **Git Bash** `bash scripts/smoke_test.sh` (PowerShell รัน `.sh` ไม่ได้) · repo ตั้ง `.gitattributes` ให้ `.sh` เป็น LF แล้ว ถ้าเคย clone ก่อนหน้านี้แล้วเจอ `$'\r': command not found` ให้ลบไฟล์นั้นแล้วดึงใหม่ครั้งเดียว `rm scripts/smoke_test.sh && git checkout -- scripts/smoke_test.sh` |
| `curl` ใน PowerShell | พิมพ์ `curl.exe` ไม่ใช่ `curl` (`curl` ใน PowerShell คือ `Invoke-WebRequest` คนละตัว) |
| ตั้งตัวแปรก่อนรันคำสั่ง | PowerShell: `$env:API_URL="http://localhost:8000"; npm run dev` (แบบ `API_URL=... npm run dev` ใช้ได้แค่ใน Git Bash) |
| Python | ใช้ `python` แทน `python3` · เปิด venv ด้วย `.venv\Scripts\activate` แทน `source .venv/bin/activate` |
| port 5432 ชน | ถ้าเครื่องลง PostgreSQL ไว้แล้ว `docker compose up` จะขึ้น `port is already allocated` → ปิด service PostgreSQL ใน Services ของ Windows ก่อน |

</details>

<details>
<summary><b>โครงของ repo</b></summary>

```
chuayduay/
├── docker-compose.yml           7 service + postgres · healthcheck ทุกตัว
├── docker-compose.override.yml  port ไว้ debug 8003-8007 + แก้โค้ดใน app/ แล้ว reload ให้เอง (ใช้เฉพาะตอน dev)
├── Makefile                     คำสั่งลัดทั้งหมด พิมพ์ make เฉย ๆ เพื่อดูรายการ
├── .env.example                 ชื่อ env ทุกตัวพร้อมค่าตัวอย่างที่ปลอดภัย
├── docs/                        เอกสารกลาง อ่านก่อนเขียนโค้ด
├── scripts/                     smoke test + ตัววัดผลทั้งระบบ
├── eval/                        ชุดทดสอบและรายงานผล
├── 08_monitoring_deployment/    งานฝั่ง infra
└── services/
    ├── 01_web_app/              Next.js 14 · ฟัง 3000
    └── 02_ … 07_                FastAPI · ฟัง 8000 เหมือนกันหมด
        ├── app/main.py          endpoint ทั้งหมดของ service นั้น
        ├── app/schemas.py       Pydantic ตาม CONTRACT — ห้ามเปลี่ยนชื่อ field
        ├── app/common.py        ของกลาง: health / X-Request-ID / log JSON
        ├── Dockerfile           ของหัวหน้า ต้องเพิ่ม system package ให้บอกก่อน
        └── README.md            วิธีรันเดี่ยวและสิ่งที่ต้องแทน
```

</details>

---

## กติกาการส่งงาน

- คนละหนึ่งโฟลเดอร์ คนละหนึ่ง branch — **แก้ได้เฉพาะ `services/<โฟลเดอร์ของตัวเอง>/`**
- branch ของแต่ละคนคือ `feature/<เลขโมดูล>-<ชื่อโมดูล>-<github username>` เช่น `feature/05-retrieval-SoSick41`
- เข้า `develop` ผ่าน Pull Request เท่านั้น **ห้าม push ตรง** · ต้องมีคน approve 1 คน
- `main` รับ merge จาก `develop` อย่างเดียว ต้อง approve 2 คน
- เจอบั๊กในงานคนอื่น → **เปิด Issue แท็กเจ้าของ ห้ามแก้เอง** เจ้าของจะได้รู้ว่าของตัวเองพัง
- แก้ `docs/CONTRACT.md` ต้องแยกเป็น PR ของตัวเอง และบอกใน `#contract-changes` ก่อน
- ห้าม commit `.env`, API key, ไฟล์โมเดล, ดัชนี หรือไฟล์เกิน 5 MB
- commit บ่อย ๆ ทุกวัน **และเปิด PR ด้วยตัวเอง** อย่าให้คนอื่น push แทน ไม่งั้น commit จะขึ้นชื่อคนอื่น

`.github/CODEOWNERS` ผูกโฟลเดอร์กับเจ้าของไว้แล้ว GitHub จะขอ review จากคนที่ถูกต้องให้อัตโนมัติทุก PR

**แจ้งเตือนอัตโนมัติเข้า Discord** — เปิด / merge / ปิด PR เข้า `#pull-requests` พร้อม ping เจ้าของโมดูลนั้น · PR หรือ push ที่แตะ `docs/CONTRACT.md` เข้า `#contract-changes` ทันที เพราะเป็นไฟล์เดียวที่พังแล้วกระทบทั้งทีม · PR ที่เป็น draft จะไม่กวนใครจนกว่าจะกด Ready for review

---

## เอกสาร

| ไฟล์ | อ่านเมื่อไหร่ |
|---|---|
| [`docs/00_PLAN_OVERVIEW.md`](docs/00_PLAN_OVERVIEW.md) | อ่านก่อนอย่างอื่น — ภาพรวม สถาปัตยกรรม ข้อตกลงของทีม ความเสี่ยงที่ประเมินไว้ |
| [`docs/CONTRACT.md`](docs/CONTRACT.md) | **กฎสูงสุด** รูปแบบ JSON ทุกเส้น ชื่อ env ทุกตัว — โค้ดขัดกับมันเมื่อไหร่ถือว่าโค้ดผิด |
| [`docs/SCHEDULE.md`](docs/SCHEDULE.md) | ใครต้องส่งอะไรวันไหน วันไหนคุณรอใคร ใครรอคุณ |
| [`docs/GIT_FLOW.md`](docs/GIT_FLOW.md) | วิธีใช้ git ของทีม — ไม่เคยใช้ git มาก่อนก็อ่านแค่หัวข้อ 0 ถึง 4 พอ |

รายละเอียดงานของแต่ละคนอยู่ในไฟล์ที่ปักหมุดในห้อง Discord ของโมดูลนั้น
