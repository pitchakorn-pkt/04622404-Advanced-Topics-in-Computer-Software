# 05 Retrieval

compose service: `retrieval` · ฟัง `0.0.0.0:8000` ข้างใน container · dev port `localhost:8005`

Hybrid retrieval สำหรับคลังความรู้ปัญหามือถือ/คอมพิวเตอร์: BM25 (ตัดคำไทยด้วย pythainlp) +
vector search (`intfloat/multilingual-e5-base` ผ่าน ChromaDB) รวมด้วย Reciprocal Rank Fusion (RRF)

## ข้อมูล

- `data/raw/daily_tech_qa.txt` — คลังหลัก 194 คู่ถาม-ตอบ 10 หมวดไทย (จากหัวหน้า)
- `data/golden_set.json` — 60 ข้อพร้อมเฉลย ใช้วัดผลใน `eval_retrieval.py`
- `data/raw/howto/*.md` — บทความ how-to จาก 04/07 (ยังไม่มีไฟล์ ณ ตอนที่เขียนนี้ ingest จะข้ามไปเงียบ ๆ)
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
| BM25 อย่างเดียว | 0.3667 | 0.6667 | 0.4753 |
| vector อย่างเดียว | 0.5500 | 0.8833 | 0.6781 |
| hybrid (RRF) | 0.4833 | 0.8000 | 0.5994 |

วัดจาก 90 chunk ที่มาจากคลัง it_support ล้วน (ยังไม่มีบทความ howto จาก 04/07) hybrid ผ่านเกณฑ์
hit@5 ≥ 80% ของ DoD แต่ยังต่ำกว่า vector อย่างเดียวในชุดนี้ — เหตุผลที่เป็นไปได้คือ BM25 อ่อนกว่า vector
มากบนคำถามแบบ paraphrase (คำไม่ตรงกับคลังเลย) ทำให้ RRF ที่ถ่วงน้ำหนักเท่ากันดึงอันดับลง
น่าจะเห็นภาพชัดขึ้นเมื่อมีบทความ howto ยาวเข้ามาเพิ่มความหลากหลายของคลัง — ของที่ลองต่อได้ถ้ามีเวลา (ดู "Could"
ใน `docs/team/05_retrieval_knowledge.md`): cross-encoder reranker บน top-20 ของผลลัพธ์ hybrid

## ไฟล์ที่ห้ามแก้

`app/common.py` เป็นของกลาง (health / X-Request-ID / log JSON) แก้ได้เฉพาะเมื่อจำเป็นจริง
`Dockerfile` เป็นของหัวหน้า ถ้าต้องเพิ่ม system package ให้บอกในช่องของตัวเอง

รายละเอียดงานทั้งหมดอยู่ในไฟล์ที่ปักหมุดในห้อง Discord ของโมดูลนี้
