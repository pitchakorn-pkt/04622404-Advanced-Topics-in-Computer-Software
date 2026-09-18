# ช่วยด้วย (ChuayDuay)

ผู้ช่วยตอบคำถามภาษาไทยเรื่องปัญหาการใช้งานมือถือและคอมพิวเตอร์ ตอบจากคลังความรู้ของระบบเองพร้อมแหล่งอ้างอิงที่ตรวจสอบได้

เป็นระบบ **agentic RAG** แยกเป็น 8 โมดูล รันด้วย Docker Compose คำสั่งเดียว
งานรายวิชา **04622404 Advanced Topics in Computer Software — DL-06 Agentic AI System I**

---

## ทีม

8 คน · 1 คนต่อ 1 โมดูล · หัวหน้าทีมดูแลโมดูล 08 และรวมงานทุกโมดูลเข้าด้วยกัน

| โมดูล | ชื่อ–สกุล | รหัสนักศึกษา | GitHub | หน้าที่ | ผลที่วัดได้ |
|---|---|---|---|---|---|
| [01 Web App](services/01_web_app/) | Jakkrich Sriraksa | 116730462014-5 | [@jakkrich0912-web](https://github.com/jakkrich0912-web) | หน้าเว็บที่ผู้ใช้เห็น — แชท แหล่งอ้างอิง ประวัติ ปุ่ม 👍👎 แผงแสดงการตัดสินใจของ agent | |
| [02 API Backend](services/02_api_backend/) | Karmolputh Phatarathorn | 116610462034-7 | [@Chakamon02](https://github.com/Chakamon02) | ประตูหน้าบ้าน — ล็อกอิน ตรวจ input ประกอบ context แล้วส่งต่อให้ router | |
| [03 AI Router](services/03_ai_router_agent/) | Patcharanat Budploy | 116730462038-4 | [@Patcharanat23](https://github.com/Patcharanat23) | สมองของระบบ — ตัดสินใจว่าคำถามไป route ไหน ด้วย 4 ชั้น guard → rules → classifier → LLM | |
| [04 AI Engines](services/04_ai_model_selection/) | Pathumporn Jorrapong | 116730462009-5 | [@pathumpornjorrapong-ops](https://github.com/pathumpornjorrapong-ops) | General AI ผ่าน Groq พร้อม fallback · Local AI โมเดลจำแนก 8 หมวดที่เทรนเอง | |
| [05 Retrieval](services/05_retrieval_knowledge/) | Suphakorn Nonthong | 116730462028-5 | [@SoSick41](https://github.com/SoSick41) | เตรียมคลังความรู้และค้นแบบ hybrid BM25 + vector — ที่มาของแหล่งอ้างอิงทุกข้อ | |
| [06 LLM Generation](services/06_llm_generation/) | Phitphibul Phrompheak | 116730462030-1 | [@phitphibul67](https://github.com/phitphibul67) | เขียนคำตอบพร้อมเลขอ้างอิงที่ตรวจแล้ว · ด่านความปลอดภัยและปิดข้อมูลส่วนตัว | |
| [07 Response / Log](services/07_response_logging/) | Jirapa Gongmool | 116730462008-7 | [@jirapa-gm](https://github.com/jirapa-gm) | ความจำของระบบ — เก็บบทสนทนา feedback และสรุปสถิติ | |
| [08 Docker / Integration](08_monitoring_deployment/) | Pitchakorn Phuadkhunthod **(หัวหน้าทีม)** | 116730462035-0 | [@pitchakorn-pkt](https://github.com/pitchakorn-pkt) | รวม 7 โมดูลให้รันด้วยคำสั่งเดียว · Docker · smoke test และวัดผลทั้งระบบ · รีวิว PR | |

branch ของแต่ละคนคือ `feature/<เลขโมดูล>-<ชื่อโมดูล>-<github username>` เช่น `feature/05-retrieval-SoSick41` ส่วนหัวหน้าทำงานผ่าน PR เข้า `develop`
ช่อง "ผลที่วัดได้" เจ้าของแต่ละโมดูลเติมเองเมื่อมีตัวเลขจริง เช่น route accuracy, hit@5, % คำตอบที่มีอ้างอิงถูกต้อง

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
| 2 classifier | โมเดลจำแนก 8 หมวดที่เทรนเอง รันในเครื่อง ถ้ามั่นใจ ≥ 0.75 | ไม่ |
| 3 LLM | เหลือเฉพาะที่ยังไม่มั่นใจ ขอคำตอบเป็น JSON | ใช่ |

ทำแบบนี้เพราะการส่งทุกคำถามให้ LLM จำแนกทั้งช้าและเปลืองโควตาที่แชร์กันทั้งทีม
`router` บันทึกไว้ทุกครั้งว่าจบที่ชั้นไหน แล้วคืนกลับมาใน `trace` เพื่อให้วัดได้ว่ากี่เปอร์เซ็นต์ไม่ต้องเรียก LLM เลย

---

## เริ่มยังไง

```bash
git clone https://github.com/pitchakorn-pkt/chuayduay.git
cd chuayduay
cp .env.example .env     # แล้วใส่ API key ของตัวเอง
make up                  # ขึ้นทั้งระบบ รอจนทุกตัว healthy
make smoke               # ทดสอบว่าต่อกันติดทั้งเส้น
```

เปิด http://localhost:3000 · ผู้ใช้ตัวอย่าง `student` / `student`

อีกสองคำสั่งที่ต้องใช้เมื่อโมดูล 05 มีของจริงแล้ว

```bash
make warmup              # ดึงโมเดล embedding ลง volume — ครั้งแรกบนเครื่องใหม่ต้องทำ
make ingest              # สร้างดัชนีค้นหาจากเอกสาร
```

ถ้า `make warmup` / `make ingest` ขึ้น `PermissionError: /models/...` หรือ `/data/index` แปลว่า volume ในเครื่องถูกสร้างไว้ตั้งแต่ก่อนแก้ Dockerfile และยังเป็นของ root อยู่ แก้ครั้งเดียวด้วย

```bash
docker compose run --rm -u root retrieval chown -R 10001:10001 /data/index /models
```

### ทำส่วนของตัวเอง — ไม่ต้องรอใคร ไม่ต้องทำ mock เอง

**ทุกโมดูลมี stub ที่ตอบตาม `docs/CONTRACT.md` อยู่แล้ว** stub พวกนี้คือ mock ของทุกคน
คุณแก้แค่โฟลเดอร์ของตัวเอง ส่วนของเพื่อนที่คุณต้องเรียกจะยังเป็น stub ที่ตอบได้เสมอ งานของใครเสร็จช้าก็ไม่ทำให้คุณติด

```bash
git checkout develop && git pull
git checkout -b feature/<เลขโมดูล>-<ชื่อ>-<github username>   # รูปแบบชื่อ branch ดูใต้ตาราง "ทีม"
docker compose up -d --wait                    # ขึ้นทั้งระบบ ของคนอื่นเป็น stub
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

### ถ้าเครื่องไม่มี `make`

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
| `make ingest` | `docker compose run --rm retrieval python ingest.py` |
| `make eval` | `python3 scripts/eval_e2e.py` |

---

## โครงของ repo

```
chuayduay/
├── docker-compose.yml           8 service + postgres · healthcheck ทุกตัว
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

---

## สถานะตอนนี้ — โครงพร้อม เนื้อยังเป็น stub

ทุก service **ตอบ JSON ตรงตาม `docs/CONTRACT.md` แล้ว** แต่ยังไม่มี logic จริงข้างใน
สิ่งที่ทำให้โครงนี้ต่างจาก stub ทั่วไปคือ **`api` กับ `router` เรียก service ถัดไปผ่าน HTTP จริง** ไม่ได้ตอบค่าปลอมอยู่ในตัวเอง
ทั้งเส้นตั้งแต่หน้าเว็บจนถึง `response-log` จึงวิ่งครบตั้งแต่วันแรก และถ้าใครต่อผิด contract จะรู้ทันทีไม่ใช่รู้ตอนรวมงาน

**งานของเจ้าของแต่ละโมดูล** คือหาคำว่า `STUB: replace` ในโฟลเดอร์ตัวเองแล้วแทนด้วยของจริง
**ห้ามเปลี่ยนรูปแบบ request / response** ถ้าคิดว่า contract ผิด ให้ทักใน `#contract-changes` ก่อน

| โมดูล | ตอนนี้ทำอะไรได้ | ที่ต้องมาแทน |
|---|---|---|
| 01 web | login + chat ต่อ `api` จริง แสดง badge route และ sources | sidebar ประวัติ, ปุ่ม 👍👎, แผง trace, อัปโหลดไฟล์, dashboard |
| 02 api | auth ด้วยผู้ใช้ตัวอย่างในหน่วยความจำ, `/api/chat` ครบเส้น, proxy ไป 07 | ต่อ postgres จริง, bcrypt, `/api/upload`, rate limit |
| 03 router | 5 route ครบด้วย keyword หยาบ ๆ, เรียก 04/05/06 จริง, คืน `trace` | cascade เต็ม 4 ชั้น, ตาราง rule base, fallback, query rewriting |
| 04 engines | `/general` และ `/local/classify` ตอบค่าปลอม | ต่อ Groq จริง + fallback provider, เทรนโมเดลจำแนก 8 หมวด |
| 05 retrieval | `/search` คืน chunk ตัวอย่าง 1 ชิ้นที่มี Source ครบ field | ingestion จริง, hybrid BM25 + vector ด้วย RRF, วัด hit@5 |
| 06 generation | 3 mode ครบ, `passthrough` ไม่เรียก LLM แล้ว | ต่อ LLM จริง, ตรวจ citation, safety + PII, prompt template |
| 07 response-log | เก็บในหน่วยความจำ, กติกา 4 ข้อทำถูกแล้ว | ต่อ postgres จริง 3 ตาราง, `/stats` คำนวณจริง |

---

## การตัดสินใจเชิงออกแบบ

เขียนไว้เพื่อให้อธิบายได้ตอนนำเสนอ และเพื่อไม่ให้มีใครไปแก้กลับโดยไม่รู้เหตุผล

**Retrieval ทำงานเฉพาะ route `university_rag`** ไม่ใช่ทุกคำถาม
ในแผนภาพต้นแบบ ทุกเส้นวิ่งผ่าน Retrieval แต่คำถามทั่วไปไม่ควรต้องไปค้นคลังความรู้ก่อน — เสียเวลาฟรีและได้ context ที่ไม่เกี่ยวมาปน
`clarify` กับ `decline` ก็ไม่เรียก service ไหนเลย

**`generation` มีโหมด `passthrough` ที่ไม่เรียก LLM**
ถ้าไม่มีโหมดนี้ คำถามเดียวจะเรียก LLM สองรอบ (ครั้งแรกที่ `engines` ครั้งที่สองที่ `generation`) ช้าขึ้นเท่าตัวและกินโควตาที่แชร์กันทั้งทีม
ตรวจได้ง่าย ๆ จาก `model: "none"` ในคำตอบ

**ชื่อ route คง `university_rag` ไว้ตามผังต้นแบบ แต่หน้าเว็บห้ามโชว์ค่าดิบ**
ความหมายจริงคือ "เส้นทางที่ตอบจากคลังความรู้ที่เราดูแลเอง พร้อมอ้างอิง" หน้าเว็บแปลงเป็นป้ายภาษาคนก่อนแสดงเสมอ

**LLM หลักคือ Groq** Gemini กับ OpenAI เป็นตัวสำรอง
ทุกเจ้าเรียกผ่านไลบรารี `openai` ตัวเดียวกัน สลับด้วย `base_url` อย่างเดียว — เปลี่ยน provider ได้ด้วยการแก้ `.env` บรรทัดเดียว ไม่ต้องแตะโค้ด
**อย่า hardcode ชื่อโมเดล** อ่านจาก `GROQ_MODEL` เสมอ เพราะผู้ให้บริการถอดโมเดลออกโดยไม่แจ้งล่วงหน้าได้

**ทุก request มี `X-Request-ID` ส่งต่อทุก hop และทุก service log เป็น JSON บรรทัดเดียว**
เวลารวมงานแล้วพัง ไล่ `request_id` เดียวกันผ่าน `make logs` จะรู้ทันทีว่าไปตายที่ hop ไหน

**`router` คืน `trace` กลับมาด้วย** บอกว่าตัดสินใจที่ชั้นไหนและใช้เวลาตรงไหนบ้าง
ข้อมูลนี้ไหลผ่านอยู่แล้วจึงไม่มีต้นทุนเพิ่ม แต่เก็บย้อนหลังไม่ได้ถ้าไม่ใส่ตั้งแต่แรก

**โมเดลกับดัชนีอยู่ใน named volume ไม่ใช่ใน image**
ไม่งั้น `build` ทุกครั้งจะโหลดใหม่เป็น GB และ image จะบวมจนแชร์กันไม่ไหว

---

## ทดสอบและวัดผล

```bash
make smoke     # ยิง /health ทุกตัว แล้วถาม 5 คำถามให้ครบทั้ง 5 route + ประวัติ + สถิติ
make eval      # รันชุดทดสอบผ่าน /api/chat จริง แล้วเขียนรายงาน
```

`make eval` เขียนออกมาสองไฟล์ — `eval/report.md` และ **`eval/report.html`** ซึ่งเป็นหน้าเว็บไฟล์เดียวจบ
เปิดด้วยการดับเบิลคลิกได้โดยไม่ต้องต่อเน็ต เอาไปเปิดโชว์ตอนนำเสนอหรือแคปใส่สไลด์ได้เลย
**ตัวเลขทุกตัวมาจากการรันจริง ไม่มีค่าที่พิมพ์เอง** และทั้งสองไฟล์อยู่ใน `.gitignore` เพราะเป็นผลรัน ไม่ใช่โค้ด

`smoke_test.sh` ครอบคลุมสามเคสที่เคยพังเงียบในระบบแบบนี้ — ขอประวัติ 10 ข้อความล่าสุดจากบทสนทนายาว,
กด feedback ทันทีก่อน log ลง DB, และขอประวัติ session ของคนอื่น

---

## กติกาการส่งงาน

- คนละหนึ่งโฟลเดอร์ คนละหนึ่ง branch — **แก้ได้เฉพาะ `services/<โฟลเดอร์ของตัวเอง>/`**
- เข้า `develop` ผ่าน Pull Request เท่านั้น **ห้าม push ตรง** · ต้องมีคน approve 1 คน
- `main` รับ merge จาก `develop` อย่างเดียว ต้อง approve 2 คน
- เจอบั๊กในงานคนอื่น → **เปิด Issue แท็กเจ้าของ ห้ามแก้เอง** เจ้าของจะได้รู้ว่าของตัวเองพัง
- แก้ `docs/CONTRACT.md` ต้องแยกเป็น PR ของตัวเอง และบอกใน `#contract-changes` ก่อน
- ห้าม commit `.env`, API key, ไฟล์โมเดล, ดัชนี หรือไฟล์เกิน 5 MB
- commit บ่อย ๆ ทุกวัน **และเปิด PR ด้วยตัวเอง** อย่าให้คนอื่น push แทน ไม่งั้น commit จะขึ้นชื่อคนอื่น

`.github/CODEOWNERS` ผูกโฟลเดอร์กับเจ้าของไว้แล้ว GitHub จะขอ review จากคนที่ถูกต้องให้อัตโนมัติทุก PR

### แจ้งเตือนอัตโนมัติเข้า Discord

| เมื่อไหร่ | ไปที่ไหน |
|---|---|
| เปิด / merge / ปิด PR | `#pull-requests` พร้อมบอกว่าเป็นโมดูลไหน ใครเปิด เปลี่ยนกี่ไฟล์ และ ping เจ้าของโมดูลนั้น |
| มี PR หรือ push แตะ `docs/CONTRACT.md` | `#contract-changes` แจ้งทุกคนทันที เพราะเป็นไฟล์เดียวที่พังแล้วกระทบทั้งทีม |

PR ที่เป็น draft จะไม่กวนใคร จนกว่าจะกด Ready for review

---

## เอกสาร

| ไฟล์ | อ่านเมื่อไหร่ |
|---|---|
| [`docs/00_PLAN_OVERVIEW.md`](docs/00_PLAN_OVERVIEW.md) | อ่านก่อนอย่างอื่น — ภาพรวม สถาปัตยกรรม ข้อตกลงของทีม ความเสี่ยงที่ประเมินไว้ |
| [`docs/CONTRACT.md`](docs/CONTRACT.md) | **กฎสูงสุด** รูปแบบ JSON ทุกเส้น ชื่อ env ทุกตัว — โค้ดขัดกับมันเมื่อไหร่ถือว่าโค้ดผิด |
| [`docs/SCHEDULE.md`](docs/SCHEDULE.md) | ใครต้องส่งอะไรวันไหน วันไหนคุณรอใคร ใครรอคุณ |
| [`docs/GIT_FLOW.md`](docs/GIT_FLOW.md) | วิธีใช้ git ของทีม — ไม่เคยใช้ git มาก่อนก็อ่านแค่หัวข้อ 0 ถึง 4 พอ |

รายละเอียดงานของแต่ละคนอยู่ในไฟล์ที่ปักหมุดในห้อง Discord ของโมดูลนั้น
