# 05 Retrieval

compose service: `retrieval` · ฟัง `0.0.0.0:8000` ข้างใน container · dev port `localhost:8005`

Hybrid retrieval สำหรับคลังความรู้ปัญหามือถือ/คอมพิวเตอร์: BM25 (ตัดคำไทยด้วย pythainlp) +
vector search (`intfloat/multilingual-e5-base` ผ่าน ChromaDB) รวมด้วย Reciprocal Rank Fusion (RRF)

## ข้อมูล

- `data/raw/daily_tech_qa.txt` — คลังหลัก 194 คู่ถาม-ตอบ 10 หมวดไทย (จากหัวหน้า)
- `data/golden_set.json` — 60 ข้อพร้อมเฉลย ใช้วัดผลใน `eval_retrieval.py`
- `data/raw/howto/*.md` — บทความ how-to จาก 04/07 ครบ 20 เรื่องแล้ว: 10 เรื่องจาก 04 (`01-*.md` ถึง
  `10-*.md`) + 10 เรื่องจาก 07 (`person07-01-*.md` ถึง `person07-10-*.md`, ใส่ prefix `person07-` กัน
  สับสนกับเลขไฟล์ของ 04 เอง เช่น `07-321-backup-rule.md` ที่เป็นไฟล์ลำดับที่ 7 ของ 04 ไม่ใช่ของคนที่ 7)
  ก่อนหน้านี้ 05 เขียนบทความร่างแทนโควตาของ 07 ไปก่อน (`draft-for-07-*.md`) ตอนนี้ลบออกแล้วแทนด้วยของจริง
  รูปแบบไฟล์: frontmatter `---\ntitle: ...\nurl: ...\ndate: ...\n---` ตามด้วยเนื้อหาแบ่งย่อหน้าด้วยบรรทัดว่าง
- `data/manifest.csv` — สร้างอัตโนมัติจาก `ingest.py` ทุกครั้ง (ห้ามแก้มือ)

### ทำไมต้องรวมคู่ถาม-ตอบเป็นเอกสารก่อน chunk

คู่ถาม-ตอบแต่ละคู่สั้นเกินกว่าที่ `CHUNK_SIZE`/`CHUNK_OVERLAP` จะมีผลอะไร (194 record เข้า 194 chunk ออก)
`ingest.py` จึงรวมคู่ในหมวดไทยเดียวกันเป็นเอกสารเดียวก่อน (10 เอกสาร `it-<slug>`) แล้วค่อยตัด chunk ยาว
~800–1200 ตัวอักษร overlap ~150 ทับขอบคู่ถาม-ตอบ (ไม่ตัดกลางคู่)

### map golden set กลับเข้า chunk ใหม่

`relevant_chunk_ids` ใน golden set คือ index ของคู่ถาม-ตอบเดิม (0-based เรียงทั้งไฟล์ ไม่ใช่ต่อหมวด)
ตอน ingest แต่ละ chunk จะเก็บ `source_qa_indices` (metadata ภายใน ไม่ใช่ field ของ CONTRACT) ไว้ว่าคุมคู่ไหนบ้าง
`eval_retrieval.py` ใช้ค่านี้ map `relevant_chunk_ids` เดิม -> ชุด `chunk_id` ใหม่ ก่อนคำนวณ hit@k/MRR

### หมวดเอกสาร vs หมวด classifier (คุยกับ 04 แล้วต้องล็อกใน PR)

`category` ของเอกสารตาม CONTRACT เป็น `it_support` ทั้งหมด (หมวดไทยเดิมเก็บแยกเป็น `category_th` ใน
metadata ของ chunk ไม่ส่งออกไปนอก service) ข้อเสนอ map หมวดไทย 10 หมวด -> หมวด classifier (v1) 8 หมวด:

| หมวดไทยในคลัง | หมวด classifier |
|---|---|
| แบตเตอรี่และการชาร์จ, เครื่องช้าและพื้นที่เต็ม | `device_performance` |
| อินเทอร์เน็ตและไวไฟ | `connectivity` |
| บัญชีและรหัสผ่าน, มิจฉาชีพและความปลอดภัย | `account_security` |
| ข้อมูลและการสำรอง | `data_backup` |
| แอปและการอัปเดต | `apps_updates` |
| หน้าจอ เสียง และกล้อง | `hardware_media` |
| การเลือกซื้อและดูแลเครื่อง, การใช้งานเอกสารและงานทั่วไป | ไม่มีหมวดตรงใน 6 หมวดแรก → เสนอ `general_other` |

## Ingest (offline)

```bash
make ingest              # docker compose run --rm retrieval python ingest.py
```
ต้อง `docker compose up -d --build retrieval` ใหม่ก่อนถ้าเพิ่งแก้ `ingest.py`/`data/`/`requirements.txt`
เพราะ dev-reload mount เฉพาะ `app/` (ดู `docker-compose.override.yml`) ไม่รวมไฟล์เหล่านี้

รันเดี่ยวบนเครื่องตัวเอง (ไม่ผ่าน docker):
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
INDEX_DIR=./data/index HF_HOME=./.hf_cache python ingest.py
```

## Search (online)

```bash
uvicorn app.main:app --reload --port 8000
curl localhost:8000/health
curl -X POST localhost:8000/search -H "Content-Type: application/json" \
  -d '{"request_id":"11111111-1111-1111-1111-111111111111","query":"ชาร์จไม่เข้าเลย","top_k":5}'
```
`chunks: []` แปลว่า "ไม่เจอ" (ผลอันดับ 1 ไม่ผ่านเกณฑ์ `SEARCH_MIN_BM25_SCORE`/`SEARCH_MIN_VECTOR_SIMILARITY`) ไม่ใช่ error

## รันในระบบรวม

```bash
make up                 # ทั้งระบบ
make warmup              # ดึงโมเดล e5-base ลง volume ก่อนใช้งานจริง (ทำครั้งแรกทุกเครื่อง)
make ingest              # สร้างดัชนีจาก data/raw/
make logs s=retrieval    # ดู log เฉพาะตัวนี้
make rebuild s=retrieval
```
ตอน dev ตัวนี้เปิด port ไว้ debug ด้วย ดูเลขใน `docker-compose.override.yml` (`localhost:8005`)
แก้โค้ดใน `app/` แล้วรอ 2–4 วินาทีเห็นผลทันที ไม่ต้อง build ใหม่ — build ใหม่เฉพาะตอนแก้
`ingest.py` / `data/` / `requirements.txt` (`docker compose up -d --build retrieval`)

## ผลวัด — ทำไมต้อง hybrid

วัดด้วย golden set 60 ข้อ variant `paraphrase` (ไม่ใช้ `verbatim` เพราะทุกวิธีจะได้ 1.0000 เท่ากันหมด
แล้วตารางไร้ความหมาย — บทเรียนจากระบบเดิม) รันได้ด้วย:
```bash
python eval_retrieval.py
```

| วิธีค้น | hit@1 | hit@5 | MRR |
|---|---|---|---|
| BM25 อย่างเดียว | 0.4000 | 0.6500 | 0.4794 |
| vector อย่างเดียว | 0.5000 | 0.8500 | 0.6325 |
| hybrid (RRF) | 0.4667 | 0.8500 | 0.6011 |
| hybrid + cross-encoder rerank | **0.7167** | **0.9333** | **0.7978** |

วัดจากคลังเต็ม 130 chunk (30 เอกสาร: 10 it_support + 20 howto จาก 04 และ 07 ของจริงครบทั้งคู่แล้ว)
hybrid ผ่านเกณฑ์ DoD (hit@5 ≥ 80%) ที่ 85% เท่ากับ vector ล้วน ๆ พอดี — ปรับ `RRF_K` จาก 60 (ค่ามาตรฐาน
งานวิจัยต้นฉบับ ออกแบบมาสำหรับ web-scale) ลงเหลือ **5** เพราะคลังเรามีแค่หลักร้อย chunk ค่า k ใหญ่ทำให้
RRF แยกแยะอันดับต้น ๆ ไม่ออก (วัดจริงแล้ว k=60 ให้ hit@5 แค่ ~77% บนคลังขนาดนี้) การปรับนี้เป็นการจูน
ค่าคงที่ร่วมของ RRF เอง ไม่ใช่การถ่วงน้ำหนักระหว่าง BM25/vector แยกกันซึ่งเป็นสิ่งที่ RRF ถูกเลือกมาเพื่อ
เลี่ยงตั้งแต่แรก

เพิ่ม **cross-encoder reranker** (`BAAI/bge-reranker-v2-m3`, ดู `app/reranker.py`) ต่อท้าย hybrid: ดึง
top-20 จาก RRF มาจัดอันดับใหม่ด้วย cross-encoder ก่อนตัดเหลือ top_k ผลคือแซงทุกวิธีอื่นชัดเจนในทุก metric

**⚠️ ปิดเป็นค่าเริ่มต้น (`RERANK_ENABLED=false`) — ยังไม่ production-ready บน CPU เดี่ยว**
วัดจริงเจอสองข้อจำกัด ไม่ใช่แค่แรม:
1. **แรม**: โหลด `bge-reranker-v2-m3` (~568M พารามิเตอร์) คู่กับ `e5-base` กิน RAM รวม **~4.3GB** ชน
   เพดาน `memory: 4G` ของ service นี้ใน `docker-compose.yml` พอดี (เสี่ยง container โดน OOM kill)
2. **เวลา (ตัวปัญหาหลัก)**: rerank 20 candidate ใช้เวลา **~15 วินาทีต่อ request** (วัดแบบ steady-state
   หลัง warmup) ชนงบเวลา router→retrieval ที่ CONTRACT กำหนดไว้ 15s พอดีเป๊ะ แทบไม่เหลือ margin เลย —
   ลองลดด้วย bfloat16 เพื่อประหยัดแรมแล้วกลับ**ช้าลงไปอีก** (~34s) เพราะ CPU เครื่องที่ทดสอบไม่มี
   bf16 compute path ที่เร็ว จึงไม่ใช่ทางแก้

ทางแก้ที่ยังไม่ได้ลอง (ใครอยากต่อยอดได้): เปลี่ยนไป cross-encoder ที่เล็ก/เร็วกว่า, ลด
`RERANK_CANDIDATE_POOL` ลงจาก 20, หรือขอเพิ่มเพดานแรมเป็น ~6G (ไฟล์ `docker-compose.yml` เป็นของหัวหน้า)
— แต่ข้อจำกัดเรื่องเวลาต้องแก้ก่อนถึงจะเอาไปต่อกับ router จริงได้ ตอนนี้เปิดทดสอบเองได้ด้วย
`RERANK_ENABLED=true` เฉพาะตอน demo/dev ที่ไม่ผ่าน router (เช่นยิง `/search` ตรง ๆ ดูคุณภาพผลลัพธ์)

## ไฟล์ที่ห้ามแก้

`app/common.py` เป็นของกลาง (health / X-Request-ID / log JSON) แก้ได้เฉพาะเมื่อจำเป็นจริง
`Dockerfile` เป็นของหัวหน้า ถ้าต้องเพิ่ม system package ให้บอกในช่องของตัวเอง

รายละเอียดงานทั้งหมดอยู่ในไฟล์ที่ปักหมุดในห้อง Discord ของโมดูลนี้
