# LAB01 — LLM Data Pipeline

ภาษาไทย · [English](README.md)

**ส่วนของผม: Cleaning + Normalization** (ขั้นที่ 2) และภายหลังคือตัว embedding แบบรันในเครื่อง
เพื่อให้ pipeline เดินได้โดยไม่ต้องมี API key ที่เสียเงิน

| ไฟล์ | |
|---|---|
| `Pipeline/cleaning.py` | `clean()` ลบ HTML, boilerplate และบรรทัดซ้ำ; `normalize()` ทำ Unicode NFC, ยุบเลขไทยกับวรรณยุกต์ซ้ำ และจัดช่องว่าง |
| `Pipeline/02_data_cleaning.py` | รันขั้นตอนนี้กับผลลัพธ์ของขั้น Collection ทุกไฟล์ แล้วพิมพ์ตัวอย่างก่อน-หลัง |
| `Pipeline/outputs/cleaned_*.json` | ผลลัพธ์ 180 records |
| `Pipeline/outputs/boilerplate_lines.json` | boilerplate ที่รอบนั้นตรวจเจอ |
| `Pipeline/embedding.py` | เพิ่ม `SentenceTransformersProvider`: `BAAI/bge-small-en-v1.5` ผ่าน sentence-transformers, 384 มิติ, รันในเครื่อง |
| `Pipeline/vector_store.py` | ตอบด้วย Groq `llama-3.3-70b-versatile`; คำถามถูก embed ด้วย provider ตัวเดียวกับที่สร้างคลัง |
| `main.py`, `requirements.txt`, `.env.example` | การต่อสายและการติดตั้งของสองข้อข้างบน |

**ของทีมที่ใช้เป็น input:** ขั้น Collection (ขั้นที่ 1) — `Pipeline/01_data_collection.ipynb`
และ `Pipeline/outputs/extracted_text_*.json` ส่วน Chunking (ขั้นที่ 3), metadata (ขั้นที่ 4)
และสคริปต์ที่ขับสองขั้นสุดท้ายก็เป็นงานของทีมเช่นกัน โฟลเดอร์นี้คือภาพรวมของ pipeline
ทั้งก้อนที่ใช้ร่วมกัน ไม่ใช่เฉพาะส่วนของผม

**ไม่ใช่ส่วนหนึ่งของ pipeline:** `LLM_data_processing.ipynb` ที่อยู่บนสุดของโฟลเดอร์นี้คือ
โน้ตบุ๊กประกอบวิชา Chapter 2 เก็บไว้เพื่ออ้างอิง มันครอบคลุมเนื้อหาเดียวกันตั้งแต่ collection
ถึง retrieval แต่ใช้ TF-IDF (`sklearn`) กับ `SimpleVectorDatabase` ในหน่วยความจำแทนโมเดล
embedding และฐานข้อมูลจริง จึงรันจบในไม่กี่วินาทีโดยไม่ต้องใช้ key — และจบที่ขั้น retrieval
ไม่มีขั้นสร้างคำตอบ

## ลำดับเวลา

**2026-07-28 — Cleaning + Normalization** ([PR #1](https://github.com/Automatic28m/Advance-AI-RAG/pull/1), merged เป็น `aca605e`)

`clean()` กับ `normalize()` เป็นสองฟังก์ชันที่เรียกแยกกันได้ แต่ใช้งานต่อกัน สองเรื่องที่ได้มาจาก
การอ่านข้อมูลจริงแทนที่จะอ่านแต่สเปก อย่างแรกคือ input มาเป็นสอง schema ไม่ใช่แบบเดียว —
Jobicy เป็น camelCase ใช้ id เป็นจำนวนเต็ม ส่วน AIDevBoard เป็น snake_case ใช้ UUID
แต่ทั้งคู่ยึด `id` เหมือนกัน อย่างที่สองคือ `jobExcerpt` ต้องได้รับการยกเว้นจากการตัด boilerplate
เพราะมันคือช่วงต้นของ `jobDescription` ซึ่งมักเป็นคำโปรยของบริษัท การตัดทิ้งทำให้ field นี้
ว่างเปล่าไป 30 จาก 160 record ส่วนบรรทัดที่ยาวไม่เกินสี่คำถูกเก็บไว้ด้วยเหตุผลคล้ายกัน —
มันคือหัวข้อย่อย ซึ่งขั้น chunking ใช้เป็นขอบเขต บันทึกเรื่อง schema ส่งให้ทีมไว้เป็นคอมเมนต์ใน PR

**2026-07-31 — embedding ในเครื่องและโมเดลตอบคำถามที่ใช้ฟรี** ([PR #11](https://github.com/Automatic28m/Advance-AI-RAG/pull/11), merged เป็น `143068b`)

ทีมเจอ `HTTP 429` เพราะโควตา embedding ของ Gemini หมด และเจอ `HTTP 404` กับ
`gemini-2.5-flash` จาก key บางใบ ทำให้สองขั้นสุดท้ายรันไม่ได้ ตอนนี้ embedding รันในเครื่อง
เป็นค่าตั้งต้นและไม่ต้องใช้ key เลย: 518 เวกเตอร์ในราว 13 วินาที โมเดลที่เลือกคือ
`BAAI/bge-small-en-v1.5` ไม่ใช่ MiniLM ที่นิยมกว่า เพราะขีดจำกัด input ที่ตั้งไว้ของ MiniLM
คือ 128 โทเคน ส่วน bge รับได้ 512 — วัดกับคลังนี้จริงแล้ว MiniLM ตัดเนื้อหาทิ้งเงียบ ๆ 72.7%
ของ chunk เทียบกับ 2.6% ของ bge

ส่วนการตอบคำถามย้ายไปใช้ free tier ของ Groq บน `llama-3.3-70b-versatile` แทน
`llama-3.1-8b-instant` เพราะจากคำถามทดสอบสี่ข้อ โมเดล 8b ลอก UUID ของแหล่งที่มาผิดไป
หนึ่งตัวอักษร ซึ่งตัวตรวจ citation จับได้ว่าเป็นการกุขึ้นมา และไม่มีอะไรถูกลบทิ้งเพื่อเปิดทาง —
provider ของ Gemini และ OpenAI ยังอยู่ครบในฐานะตาข่ายรับและเป็นตัวเทียบสำหรับรายงาน

อีกสองรายละเอียดที่เสียเวลาไปมากและควรบันทึกไว้ Groq ตอบ `403` ไม่ใช่ `404` เมื่อ Cloudflare
ปฏิเสธ user agent `Python-urllib/3.x` (`error code: 1010`) และรีโปนี้คุย HTTP ผ่าน `urllib`
ล้วน ทางแก้คือส่ง `User-Agent` จริงไป และ `post_with_retry` เคยทิ้ง response body ทำให้
ความล้มเหลวทุกแบบหน้าตาเหมือนกันหมดจากข้างนอก ตอนนี้มัน log body ออกมาแล้ว

## กฎตัด boilerplate แลกอะไรไป

การตัด boilerplate จะลบบรรทัดที่ปรากฏในเอกสารตั้งแต่ห้าฉบับขึ้นไป ด้วยเหตุผลว่าบรรทัดที่ซ้ำกัน
ข้ามประกาศที่ไม่เกี่ยวกันคือคำโปรยบริษัทหรือข้อความเรื่องความเท่าเทียม ไม่ใช่เนื้อหาของงาน
เหตุผลนี้ใช้ได้ก็ต่อเมื่อประกาศแต่ละฉบับเป็นอิสระต่อกัน ซึ่งคลังนี้ไม่ใช่ — Canonical คิดเป็น 36
จาก 160 ประกาศฝั่ง Jobicy, Nebius 9, Experian 7 และ iHerb 5 ประกาศของนายจ้างรายเดียวกัน
ย่อมซ้ำกันเองโดยธรรมชาติ บรรทัดของมันจึงข้ามเส้นห้าเอกสารได้โดยไม่ต้องเป็น boilerplate เลย

วัดจากผลลัพธ์ที่ commit ไว้ คิดเป็นสัดส่วนข้อความของนายจ้างแต่ละรายที่รอดจากการ clean:

| นายจ้าง | จำนวนประกาศ | ข้อความที่เหลือ |
|---|---|---|
| นายจ้าง 58 รายที่ลงประกาศใบเดียว | รายละ 1 | 86% |
| Experian | 7 | 86% |
| Canonical | 36 | 59% |
| iHerb | 5 | 34% |

บรรทัดทั้ง 77 บรรทัดใน `outputs/boilerplate_lines.json` ส่วนใหญ่คือสิ่งที่กฎนี้ถูกเขียนขึ้นมาเพื่อ
กำจัด แต่ไม่ใช่ทั้งหมด `Experience with Linux (Debian or Ubuntu preferred)` อยู่ในนั้น
เช่นเดียวกับ `Experience with Microsoft Office Suite (Word, Excel, PowerPoint)` และ
`Bachelor's Degree in Computer Science or related field preferred` — ทั้งหมดคือคุณสมบัติที่
รับสมัคร ถูกลบออกจากทุกประกาศที่ระบุมันไว้ เรื่องนี้ลามไปถึงตัวอย่างคำถามใน README ฉบับนี้เอง:
การค้นว่าใครรับสมัครงานด้าน Kubernetes ถูกตอบจากประกาศที่ข้อความระบุความต้องการ Linux
ไม่เหลืออยู่แล้ว

ไม่มีอะไรตรงนี้ที่โค้ดทำต่างไปจากที่มันบอกไว้ สิ่งที่ควรทบทวนคือตัวเกณฑ์: ถ้านับจำนวน*นายจ้าง*
ที่ใช้บรรทัดนั้นแทนจำนวนเอกสาร ก็จะแยกคำโปรยที่หลายบริษัทใช้ซ้ำกัน ออกจากคุณสมบัติที่บริษัท
เดียวใช้ซ้ำได้ ที่ยังไม่เปลี่ยนตรงนี้เพราะขั้นตอนถัด ๆ ไปถูกสร้างและวัดผลบนผลลัพธ์ชุดที่ clean
ด้วยกฎปัจจุบัน

ดึงเข้ามาด้วย `git subtree` จาก [Automatic28m/Advance-AI-RAG](https://github.com/Automatic28m/Advance-AI-RAG) branch `Develop`

---

# Advance Topics in Computer Software course
## Computer Engineering - RMUTT
## จุดประสงค์คือศึกษา 8 ขั้นตอนของ LLM data pipeline ตั้งแต่ Data Collection จนถึง LLM / Retrieval เพื่อเรียนรู้วิธีการของ RAG หรือ Retrieval-Augmented Generation
## วิธีรัน

Python 3.12 ขั้น embedding รันในเครื่องนี้และไม่ต้องใช้ API key มีเพียงขั้นสุดท้ายที่ให้โมเดล
เขียนคำตอบเท่านั้นที่ต้องใช้

```bash
pip install -r requirements.txt

python Pipeline/04_metadata.py     # ใส่ metadata ให้ chunk ที่ commit ไว้ในนี้
python Pipeline/05_embedding.py    # embed ในเครื่อง ไม่ต้องใช้ key ราว 13 วินาที
python main.py --build             # สร้าง index ลง Pipeline/chroma_db
```

จากนั้นลองถามอะไรสักอย่าง

```bash
# ค้นคืนอย่างเดียว: พิมพ์ข้อความที่เจอพร้อมคะแนน ไม่ต้องใช้ key
python main.py --no-llm -q "which companies hire for Kubernetes"

# คำถามเดียวกัน ตอบเป็นร้อยแก้วโดยมี citation กำกับทุกข้อความ
python main.py -q "which companies hire for Kubernetes"
```

คำสั่งที่สองอ่าน `GROQ_API_KEY` จาก `Pipeline/.env` (ขอ key ฟรีได้ที่
<https://console.groq.com/keys>) ให้ก็อป `Pipeline/.env.example` แล้วเติมค่าลงไป
รัน `python main.py` โดยไม่ใส่ `-q` เพื่อถามต่อเนื่องแบบโต้ตอบ

`embeddings_*.json` และ `chroma_*/` เป็นของที่สร้างขึ้นมา ไม่ใช่ต้นทาง จึงถูก gitignore ไว้
สามคำสั่งข้างบนสร้างมันขึ้นใหม่จากสิ่งที่ commit ไว้ ซึ่งเป็นเหตุผลว่าทำไมทั้งสามคำสั่งไม่มีค่าใช้จ่าย

ถ้าจะ embed ผ่าน API แทนการรันในเครื่อง ให้เลือก provider แล้วให้มันมีที่เก็บของตัวเอง —
เวกเตอร์คนละความกว้างอยู่ collection เดียวกันไม่ได้

```bash
python Pipeline/05_embedding.py --provider gemini --dimension 1536
python main.py --build --collection job_postings_gemini --persist-dir Pipeline/chroma_gemini
```

## สมาชิกในทีม
- 116730462006-1 Phanlop Boonluea
- 116730462011-1 Saran Tanyavikai
- 116730462016-0 Sakda Baokam
- 116730462032-7 Praphavit Kaorak
- 116730462033-5 Praphakorn Pitamma
- 116730462035-0 Pitchakorn Phuadkhunthod
