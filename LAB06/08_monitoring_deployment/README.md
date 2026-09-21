# 08 Docker / Integration / Monitoring

โฟลเดอร์นี้กับไฟล์ที่ราก (`docker-compose*.yml`, `Makefile`, `.env.example`, `scripts/`, `eval/`)
เป็นของหัวหน้าทีม ตาม `.github/CODEOWNERS`

## คำสั่งที่ใช้บ่อย

```bash
make            # ดูคำสั่งทั้งหมด
make up         # ขึ้นทั้งระบบ รอจนทุกตัว healthy
make ps         # ตัวไหนยังไม่ healthy
make logs s=router
make smoke      # ทดสอบทั้งเส้น
make eval       # รันชุดวัดผล เขียน eval/report.md + report.html
```

## `PermissionError` ตอน warmup หรือ ingest

ถ้า `make warmup` / `make ingest` ขึ้น `PermissionError: /models/...` หรือ `/data/index` แปลว่า volume ในเครื่องถูกสร้างไว้ตั้งแต่ก่อนแก้ Dockerfile และยังเป็นของ root อยู่ แก้ครั้งเดียวด้วย

```bash
docker compose run --rm -u root retrieval chown -R 10001:10001 /data/index /models
```

## ลำดับคิดเวลารวมงานแล้วพัง

1. `make ps` — ตัวไหนไม่ healthy
2. `make logs s=<ตัวนั้น>` — หา `request_id` เดียวกันไล่ทีละ hop
3. พังที่ "กล่อง" (port, env, volume, network, Dockerfile) → **หัวหน้าแก้**
4. พังที่ "ของข้างใน" (logic, schema ไม่ตรง contract) → **เปิด Issue แท็กเจ้าของ ห้ามแก้เอง**
5. contract ไม่พอหรือผิด → คุยใน `#contract-changes` แล้วแก้ผ่าน PR แยก

## Prometheus + Grafana

ยังไม่ได้ทำ เป็นงาน Could ถ้าทำให้ใส่ไว้หลัง `profiles: ["monitoring"]`
ใน compose เพื่อไม่ให้มันขึ้นมาเองตอน `make up` ปกติ

---

## คู่มือสำหรับทีม (ย้ายมาจาก README หน้าแรก)

README หน้าแรกเก็บไว้สำหรับผลที่วัดได้ ส่วนวิธีทำงานประจำวันอยู่ที่นี่

### ทำส่วนของตัวเอง — ไม่ต้องรอใคร ไม่ต้องทำ mock เอง

ทุกโมดูลตอบตาม `docs/CONTRACT.md` อยู่แล้ว แก้แค่โฟลเดอร์ของตัวเอง ส่วนของเพื่อนที่ต้องเรียกจะตอบได้เสมอ งานของใครเสร็จช้าก็ไม่ทำให้ติด

```bash
git checkout develop && git pull
git checkout -b feature/<เลขโมดูล>-<ชื่อโมดูล>-<github username>
docker compose up -d --wait                    # ขึ้นทั้งระบบ
# แก้โค้ดใน services/<โฟลเดอร์ของคุณ>/app/ → reload ให้เองภายในไม่กี่วินาที ไม่ต้อง build ใหม่
curl localhost:<port ของคุณ>/health            # ทดสอบ service ของตัวเองโดยตรง
docker compose logs -f <service ของคุณ>        # ดู error
```

| โมดูล | service | ทดสอบที่ |
|---|---|---|
| 01 web | `web` | http://localhost:3000 (หรือ `npm run dev` ดู README ของ 01) |
| 02 api | `api` | `localhost:8000` |
| 03 router | `router` | `localhost:8003` |
| 04 engines | `engines` | `localhost:8004` |
| 05 retrieval | `retrieval` | `localhost:8005` |
| 06 generation | `generation` | `localhost:8006` |
| 07 response-log | `response-log` | `localhost:8007` |

**ต้อง build ใหม่เมื่อใด** — reload อัตโนมัติดูแค่ไฟล์ใน `app/`
ถ้าแก้ `requirements.txt`, `Dockerfile` หรือไฟล์นอก `app/` (เช่น `ingest.py`, `prompts/`) ให้สั่ง `docker compose up -d --build <service>`
ส่วน `web` build ใหม่ทุกครั้งที่แก้ ถ้าจะแก้บ่อยให้ใช้ `npm run dev`

**ห้ามแก้โฟลเดอร์ของคนอื่น** หากต้องการให้โมดูลของเพื่อนตอบอะไรเพิ่ม ให้แจ้งในห้องของเขาหรือ `#contract-changes`

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
| `make warmup` | `docker compose run --rm retrieval python -c "import os; from huggingface_hub import snapshot_download; snapshot_download(os.environ['EMBEDDING_MODEL'])"` |
| `make ingest` | `docker compose run --rm retrieval python ingest.py` |
| `make eval` | `python3 scripts/eval_e2e.py` |

### ถ้าใช้ Windows

| เรื่อง | ทำแบบนี้ |
|---|---|
| ที่ clone repo | ไว้ที่ `C:\dev\chuayduay` **อย่าไว้ใน OneDrive หรือโฟลเดอร์ที่มีเว้นวรรค** — OneDrive ล็อกไฟล์ตอน sync และ docker mount โฟลเดอร์พวกนั้นแล้วพัง |
| รัน `.sh` | ใช้ **Git Bash** `bash scripts/smoke_test.sh` (PowerShell รัน `.sh` ไม่ได้) · repo ตั้ง `.gitattributes` ให้ `.sh` เป็น LF แล้ว ถ้าเคย clone ก่อนหน้านี้แล้วเจอ `$'\r': command not found` ให้ลบไฟล์นั้นแล้วดึงใหม่ครั้งเดียว `rm scripts/smoke_test.sh && git checkout -- scripts/smoke_test.sh` |
| `curl` ใน PowerShell | พิมพ์ `curl.exe` ไม่ใช่ `curl` (`curl` ใน PowerShell คือ `Invoke-WebRequest` คนละตัว) |
| ตั้งตัวแปรก่อนรันคำสั่ง | PowerShell: `$env:API_URL="http://localhost:8000"; npm run dev` (แบบ `API_URL=... npm run dev` ใช้ได้แค่ใน Git Bash) |
| Python | ใช้ `python` แทน `python3` · เปิด venv ด้วย `.venv\Scripts\activate` แทน `source .venv/bin/activate` |
| port 5432 ชน | ถ้าเครื่องลง PostgreSQL ไว้แล้ว `docker compose up` จะขึ้น `port is already allocated` → ปิด service PostgreSQL ใน Services ของ Windows ก่อน |

### โครงของ repo

```
chuayduay/
├── docker-compose.yml           7 service + postgres · healthcheck ทุกตัว
├── docker-compose.override.yml  port ไว้ debug 8003-8007 + แก้โค้ดใน app/ แล้ว reload ให้เอง (ใช้เฉพาะตอน dev)
├── Makefile                     คำสั่งลัดทั้งหมด พิมพ์ make โดยไม่ใส่อะไรต่อท้ายเพื่อดูรายการ
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
        ├── Dockerfile           หัวหน้าทีมดูแล ต้องการเพิ่ม system package ให้แจ้งก่อน
        └── README.md            วิธีรันเดี่ยวและสิ่งที่ต้องแทน
```

### กติกาการส่งงาน

- คนละหนึ่งโฟลเดอร์ คนละหนึ่ง branch — **แก้ได้เฉพาะ `services/<โฟลเดอร์ของตัวเอง>/`**
- branch ของแต่ละคนคือ `feature/<เลขโมดูล>-<ชื่อโมดูล>-<github username>` เช่น `feature/05-retrieval-SoSick41`
- เข้า `develop` ผ่าน Pull Request เท่านั้น **ห้าม push ตรง** · ต้องมีคน approve 1 คน
- `main` รับ merge จาก `develop` อย่างเดียว ต้อง approve 2 คน
- เจอบั๊กในงานคนอื่น → **เปิด Issue แท็กเจ้าของ ห้ามแก้เอง** เจ้าของจะได้ทราบว่าส่วนของตนมีปัญหา
- แก้ `docs/CONTRACT.md` ต้องแยกเป็น PR ของตัวเอง และบอกใน `#contract-changes` ก่อน
- ห้าม commit `.env`, API key, ไฟล์โมเดล, ดัชนี หรือไฟล์เกิน 5 MB
- commit บ่อย ๆ ทุกวัน **และเปิด PR ด้วยตัวเอง** อย่าให้คนอื่น push แทน ไม่เช่นนั้น commit จะขึ้นชื่อคนอื่น

`.github/CODEOWNERS` ผูกโฟลเดอร์กับเจ้าของไว้แล้ว GitHub จะขอ review จากคนที่ถูกต้องให้อัตโนมัติทุก PR

**แจ้งเตือนอัตโนมัติเข้า Discord** — เปิด / merge / ปิด PR เข้า `#pull-requests` พร้อม ping เจ้าของโมดูลนั้น · PR หรือ push ที่แตะ `docs/CONTRACT.md` เข้า `#contract-changes` ทันที เพราะเป็นไฟล์เดียวที่พังแล้วกระทบทั้งทีม · PR ที่เป็น draft จะไม่แจ้งเตือนใครจนกว่าจะกด Ready for review
