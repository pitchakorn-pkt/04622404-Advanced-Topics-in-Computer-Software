# LAB06 — Agentic AI System: ChuayDuay (team project)

English · [ภาษาไทย](README.th.md)

**Team repository: [pitchakorn-pkt/chuayduay](https://github.com/pitchakorn-pkt/chuayduay)**

ChuayDuay ("help!") is a Thai-language assistant for everyday phone and computer problems,
built by a team of eight as the DL-06 *Agentic AI System I* assignment. It is an agentic
RAG system split into eight services that talk over HTTP: a router decides, question by
question, whether to answer from our own knowledge base with citations, from a general
LLM, from a locally trained classifier, to ask the user to clarify, or to decline. The
whole stack starts with one `docker compose` command.

**My part: team lead and module 08 — Docker / Integration.** Each of the other seven
members owned one service. I owned what joins them: the repository and its rules, the
API contract every service codes against, the Docker setup, the end-to-end tests and
measurements, reviewing and merging every pull request, and the Discord server the team
worked in. The team's own README, below the line, describes the system and its measured
results; this section describes what I did.

## What I did

### 1. Set the project up so eight people could start on day one without waiting for each other

Eight people building eight services in parallel only works if nobody has to wait for
the service in front of theirs. On the first day (16 September) I put three things in
place before anyone wrote feature code:

- **The contract** — [`docs/CONTRACT.md`](docs/CONTRACT.md) fixes the JSON shape of every
  call between services and the name of every environment variable. When code and the
  contract disagree, the code is wrong. It reached v1.7 by the end; every change went
  through a pull request and set off an alert in Discord.
- **A running skeleton of all eight services** — every service existed as a working stub
  that already answered in the contract's format, and `api` and `router` really called the
  next service over HTTP. So from the first hour anyone could run the whole system, replace
  their own stub with real code, and see it work end to end — no one had to write mocks of
  someone else's service.
- **The data** — the knowledge base (`daily_tech_qa.txt`, question–answer pairs in 10
  categories) and the 60-question golden set with answer keys came from my own
  [`LAB04`](../LAB04/). Handing them over on day one meant the retrieval module could be
  built and measured immediately instead of waiting for a dataset.

The repository rules followed from one requirement of the assignment: every member's
contribution had to be visible. **One person, one folder, one branch**: each member edits
only `services/<their folder>/` on their own `feature/…` branch, gets into `develop` only
through a pull request, and `main` takes merges from `develop` only. A bug in someone
else's service is reported as an Issue tagged to its owner, not fixed on their behalf —
so the commit history shows who really did what. Branch protection enforces the review
step, and `.github/CODEOWNERS` maps each folder to its owner so GitHub asks the right
person to review every pull request automatically.

### 2. Organised the work so each member knew exactly what to do

- **A brief for every module**, posted and pinned in that member's own Discord room: what
  the module is responsible for, which folder and branch are theirs, what it receives and
  returns according to the contract, and which module waits on it. When the first briefs
  turned out to contradict the skeleton (they still asked people to build things that
  already existed), I rewrote all seven and re-pinned them on day two.
- **Shared documents** in [`docs/`](docs/): the plan overview, the schedule (who delivers
  what on which day, who waits for whom), and a git guide written for members who had never
  used git before.
- **A Discord server built by a script, not by hand.** I wrote a bot (`setup_discord.py`,
  kept outside this repository because it holds the bot token) that reads one
  `config.yaml` and creates everything: 9 roles (the lead plus one per module, so
  `@retrieval` reaches the right person), 18 channels in 3 categories — a shared area, one
  room per module, and rooms for work that crosses modules — the webhooks, and the pinned
  brief in each module room. It is idempotent, so it can be re-run after changing the
  config without creating duplicates.
- **Notifications from GitHub to Discord** ([`.github/workflows/`](.github/workflows/)):
  one workflow posts when a pull request is opened, merged or closed and mentions the
  module's owner; another posts a loud alert whenever anyone touches `CONTRACT.md`,
  because it is the one file whose breakage hits all eight people at once.

### 3. Module 08 — Docker and integration

| File | |
|---|---|
| `docker-compose.yml` | all services, PostgreSQL, health checks, and named volumes for models and the search index so images stay small and nothing re-downloads on every build |
| `docker-compose.override.yml` | development mode: edit code in `app/` and see it live in 2–4 seconds without rebuilding, including on Windows |
| `Makefile` | `make up / ps / logs / smoke / warmup / ingest / eval / backup` — one command per job, with the full `docker compose` equivalent written in the docs for machines without `make` |
| `scripts/smoke_test.sh` | 14 checks across the whole path — every service's `/health`, login, one question per route (all 5), history and statistics |
| `scripts/eval_e2e.py`, `eval/golden.jsonl` | the 64-question end-to-end evaluation called through `/api/chat` like a real user; writes `eval/report.md` and a self-contained `eval/report.html` |
| `08_monitoring_deployment/README.md` | everyday commands, how to debug a failed integration by following one `request_id` through every hop, and a section for members on Windows |

Every request carries an `X-Request-ID` through every hop and every service logs one JSON
line per event, which is what makes "which service broke?" answerable with a single
`make logs`.

### 4. Reviewed and merged every pull request

Of the 35 pull requests in the repository, 19 came from the other seven members. I
reviewed them against the contract and by running the branch on a separate copy of the
stack — **19 approvals and 5 requests for changes** in total — and merged 14 of them
myself (the rest were merged by their authors). When a member's fix was ready but not yet in
a pull request close to the presentation, I opened the pull request for them
with their commits and authorship intact (#19, module 06).

The review that mattered most was not of a diff. On 20 September I sent unusual inputs
through `/api/chat` the way a real user would — typos, mixed Thai and English, follow-up
questions, jailbreak attempts, instructions hidden inside an attached file — and reported
each finding to its owner. The serious one was a prompt injection through file content in
module 04; others were a dead end on the RAG route when the answer was not in the
knowledge base (03), greetings being asked to clarify (03), and citations of the form
`[1, 2, 3]` being dropped (06). The router and injection issues were fixed by their
owners in #22 and #25, and the rule for the RAG route went into the contract as v1.7 (#24).

### 5. Tested the whole system and wrote down the numbers

Before `develop` went to `main` I ran three layers on the real stack: the unit tests of
modules 02 and 03 plus the retrieval evaluation, then the smoke test (14/14), then the
64-question evaluation. Its results — **85.9% route accuracy, 51/60 answers with real
citations, 2.2 s average latency, 0 failed requests** — were posted on the release pull
request (#30) and are the figures in the team README below. I then rewrote the team README
so that every claim in it was checked against the code, and every number says which
command reproduces it.

## Timeline

| Date | |
|---|---|
| 16 Sep | repository, branch rules, CODEOWNERS, contract, docs, skeleton of all 8 services, Discord server and notifications |
| 17 Sep | live reload for development ([#1](https://github.com/pitchakorn-pkt/chuayduay/pull/1)); briefs rewritten and re-pinned |
| 19 Sep | volume permissions on fresh machines (#9), team table with names and student IDs (#10, #11), smoke test checks the real route + Windows section (#15), real 64-question evaluation (#16) |
| 20 Sep | fallback model moved to `gemini-3.5-flash-lite` (#20), contract v1.7 (#24), evaluation survives the chat rate limit (#29); edge-case sweep reported to owners; all 8 modules on `develop` |
| 21 Sep | release to `main` (#30), README rewritten and checked against the code (#31–#33), final release with the rating button from module 01 (#35) |

On `main`, 31 of the 89 non-merge commits are mine, and the 29 merge commits under the
name `CHAMP` are also mine (my GitHub display name).

## What is in this folder

This folder is the whole team repository, not only my part. Mine are the files at the
root (`docker-compose*.yml`, `Makefile`, `.env.example`, `scripts/`, `eval/`, `.github/`),
[`08_monitoring_deployment/`](08_monitoring_deployment/) and [`docs/`](docs/). Each folder
under [`services/`](services/) belongs to the member named in the team table below; I wrote
the first skeleton of each, which its owner then replaced. How to run it is in the section
"ทำซ้ำผลวัดเอง" below.

Pulled with `git subtree` from [pitchakorn-pkt/chuayduay](https://github.com/pitchakorn-pkt/chuayduay), branch `main`.

---

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

ทุกตัวเลขในหัวข้อนี้มาจากการรันจริงบนเครื่อง ไม่มีค่าที่พิมพ์เอง และทุกตารางระบุไว้ว่ารันซ้ำด้วยคำสั่งใด

### 1. ทั้งระบบ — ชุดทดสอบ 64 คำถาม เรียกผ่าน `/api/chat` เหมือนผู้ใช้จริง

| ตัวชี้วัด | ค่า | วัดอะไร |
|---|---|---|
| เลือกเส้นทางถูก (route accuracy) | **85.9%** · 55/64 | router ส่งคำถามไป route ที่เฉลยระบุไว้ได้กี่ข้อ |
| คำตอบสาย RAG ที่มีแหล่งอ้างอิงจริง | **51/60** | คำถามที่ควรตอบจากคลังความรู้ แล้วได้คำตอบที่แนบเลขอ้างอิงกลับมาจริง |
| เวลาตอบเฉลี่ย | **2.2 วินาที** | นับตั้งแต่ `api` รับคำถามจนตอบกลับครบ รวมทุก hop ที่เส้นทางนั้นต้องผ่าน |
| เวลาตอบ p95 | **3.7 วินาที** | ช้าที่สุดของ 95% แรก — ตัวบอกว่าเคสหนักยังอยู่ในเกณฑ์ |
| คำขอที่ล้มเหลว | **0** | ไม่มีข้อไหนได้ error กลับมา · 9 ข้อที่ไม่ผ่านคือเลือก route ไม่ตรงเฉลย ไม่ใช่ระบบพัง |

รันซ้ำด้วย `make eval` → เขียน `eval/report.md` และ `eval/report.html` ที่ลงรายละเอียดครบทั้ง 64 ข้อ
ชุดนี้รันด้วย `gemini-3.5-flash-lite` เว้นระยะ 10 วินาทีต่อข้อ เพื่อกันโควตารายวันของ Groq ไว้ใช้วันนำเสนอ

> [!NOTE]
> **อ่านเลข route accuracy ควบคู่กับสัดส่วนของชุดทดสอบ** — 64 ข้อนั้นเป็น `university_rag` 60 ข้อ ที่เหลือ `general_ai` / `local_ai` / `clarify` / `decline` หมวดละ 1 ข้อ ตั้งใจถ่วงไปทางคลังความรู้เพราะเป็นเส้นทางหลักที่ต้องมีแหล่งอ้างอิง ผลคือชุดนี้นำไปเทียบกับ benchmark ที่แบ่งหมวดเท่ากันไม่ได้ และ majority-class baseline ซึ่งตอบ `university_rag` ทุกข้อจะได้ 60/64 บนชุดนี้ · ส่วน "คำตอบสาย RAG ที่มีแหล่งอ้างอิงจริง" นับจาก 60 ข้อนั้นโดยตรง จึงไม่ได้รับผลจากสัดส่วนนี้

### 2. การค้นคลังความรู้ — วัดกับ golden set 60 คำถามที่มีเฉลยว่าเอกสารไหนถูก

| วิธีค้น | hit@1 | hit@5 | MRR |
|---|---|---|---|
| BM25 อย่างเดียว | 0.4000 | 0.6500 | 0.4794 |
| vector อย่างเดียว | 0.5000 | 0.8500 | 0.6325 |
| **hybrid (RRF) — ที่ระบบใช้จริง** | **0.4667** | **0.8500** | **0.6011** |
| hybrid + cross-encoder rerank | 0.7167 | 0.9333 | 0.7978 |

**hit@5** = เอกสารเฉลยติดอยู่ใน 5 อันดับแรกกี่เปอร์เซ็นต์ · **MRR** = ค่าเฉลี่ยของส่วนกลับของอันดับที่เจอเฉลย ยิ่งสูงแปลว่ายิ่งดันเฉลยขึ้นไปอยู่บน
วัดบนคลังเต็ม 130 chunk · รันซ้ำด้วย `docker compose run --rm --no-deps retrieval python eval_retrieval.py` (ใช้เวลาราว 13 นาที เพราะแถว rerank ต้องรันโมเดลบน CPU)
rerank ดีขึ้นจริงทั้งสามค่า แต่ปิดไว้เป็นค่าเริ่มต้น เหตุผลอยู่ในหัวข้อ "ข้อจำกัดที่รู้อยู่"

### 3. ชุดทดสอบอัตโนมัติ

| ชุด | ผล | รันซ้ำด้วย |
|---|---|---|
| smoke test — ทั้งเส้นครบ 5 route + ประวัติ + สถิติ | **14/14** | `make smoke` |
| unit test ของ 03 AI Router | **87 ผ่าน** | `docker compose run --rm --no-deps router sh -c "pip install -q pytest && python -m pytest tests -q"` |
| unit test ของ 02 API Backend | **31 ผ่าน** | `docker compose exec api python -m pytest -q` |
| โมเดลจำแนกหมวดของ 04 (cross-validation 5-fold) | **82.07%** | `docker compose run --rm --no-deps engines python train.py` |

82.07% คือความแม่นของตัวโมเดลเอง วัดบน 357 ตัวอย่าง 8 หมวดด้วย cross-validation ไม่ใช่ความแม่นของทั้งระบบ · ในระบบจริง router รับผลของโมเดลนี้เฉพาะตอนที่มั่นใจ ≥ 0.75 เท่านั้น คำถามที่ต่ำกว่านั้นตกไปให้ LLM ตัดสินในชั้นถัดไป

---

## ระบบทำงานอย่างไร

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

| ชั้น | ทำอะไร | เรียก LLM หรือไม่ |
|---|---|---|
| 0 guard | ข้อความว่าง สั้นเกิน อ้างอิงถึงสิ่งที่ไม่ได้ระบุ → `clarify` · คำขอที่ไม่ควรตอบ → `decline` | ไม่ |
| 1 rules | คำสำคัญของโดเมน (ไวไฟ รหัสผ่าน แบต เครื่องช้า …) → `university_rag` | ไม่ |
| 2 classifier | โมเดลจำแนก 8 หมวดที่เทรนเอง รันในเครื่อง ใช้เมื่อมั่นใจ ≥ 0.75 | ไม่ |
| 3 LLM | เหลือเฉพาะที่ยังไม่มั่นใจ ขอคำตอบเป็น JSON | ใช่ |

ทำแบบนี้เพราะการส่งทุกคำถามให้ LLM จำแนกทั้งช้าและเปลืองโควตาที่แชร์กันทั้งทีม
`router` บันทึกทุกครั้งว่าจบที่ชั้นไหนแล้วคืนกลับมาใน `trace` จึงวัดได้ว่ากี่เปอร์เซ็นต์ไม่ต้องเรียก LLM เลย

**สิ่งที่ระบบทำได้ตอนนี้** — ล็อกอิน · ถาม-ตอบต่อเนื่องจำบริบทเดิมได้ · แสดงแหล่งอ้างอิงใต้คำตอบ · ประวัติแชทย้อนหลัง · เปิดดูการตัดสินใจของ agent · คัดลอกคำตอบ · การ์ดสถิติการใช้งาน · ปิดข้อมูลส่วนตัวในคำตอบอัตโนมัติ · สลับผู้ให้บริการ LLM เองเมื่อเจ้าหลักล่มหรือโควตาหมด

---

## การตัดสินใจเชิงออกแบบ

เขียนไว้เพื่อให้อธิบายได้ตอนนำเสนอ และเพื่อไม่ให้มีใครไปแก้กลับโดยไม่รู้เหตุผล

**Retrieval ทำงานเฉพาะ route `university_rag`** ไม่ใช่ทุกคำถาม
ในแผนภาพต้นแบบทุกเส้นวิ่งผ่าน Retrieval แต่คำถามทั่วไปไม่ควรต้องไปค้นคลังความรู้ก่อน — เสียเวลาฟรีและได้ context ที่ไม่เกี่ยวมาปน · `clarify` กับ `decline` ไม่เรียก service ไหนเลย

**`generation` มีโหมด `passthrough` ที่ไม่เรียก LLM**
ถ้าไม่มีโหมดนี้ คำถามเดียวจะเรียก LLM สองรอบ (ที่ `engines` และที่ `generation`) ช้าขึ้นเท่าตัวและกินโควตาที่แชร์กันทั้งทีม · ตรวจได้จาก `model: "none"` ในคำตอบ

**เส้น `university_rag` ห้ามจบด้วยการบอกผู้ใช้ว่าไม่มีข้อมูล**
ถ้าค้นไม่เจอ หรือเจอแต่เรียบเรียงคำตอบไม่ได้ ระบบจะถอยไปตอบด้วยความรู้ทั่วไปแล้วบอกตรง ๆ ว่าคำตอบนี้ไม่ได้อ้างอิงเอกสาร — ดีกว่าปล่อยให้ผู้ใช้ได้ข้อความว่า "ไม่พบข้อมูล" แล้วจบการสนทนา

**ชื่อ route คง `university_rag` ไว้ตามผังต้นแบบ แต่หน้าเว็บห้ามแสดงค่าดิบ**
ความหมายจริงคือ "เส้นทางที่ตอบจากคลังความรู้ที่เราดูแลเอง พร้อมอ้างอิง" หน้าเว็บแปลงเป็นป้ายภาษาไทยที่ผู้ใช้เข้าใจก่อนแสดงเสมอ

**LLM หลักคือ Groq มี Gemini เป็นตัวสำรองที่สลับให้เองอัตโนมัติ** เมื่อเจ้าหลักล่มหรือโควตาหมด
ตาราง provider มี OpenAI อยู่ด้วย แต่ระบบวนลองทีละคู่ตาม `LLM_PRIMARY` → `LLM_FALLBACK` เท่านั้น ไม่ได้ไล่ครบทั้งสามเจ้า
ทุกเจ้าเรียกผ่านไลบรารี `openai` ตัวเดียวกัน สลับด้วย `base_url` อย่างเดียว — เปลี่ยนผู้ให้บริการได้ด้วยการแก้ `.env` บรรทัดเดียว ไม่ต้องแตะโค้ด

**เนื้อหาจากไฟล์ที่ผู้ใช้แนบมาเป็น "ข้อมูล" ไม่ใช่ "คำสั่ง"**
วางเนื้อไฟล์ไว้ก่อนแล้วปิดท้ายด้วยคำสั่งจริงของผู้ใช้เสมอ พร้อมตัด role marker ปลอมออก — วัดแล้วว่าการเรียงกลับด้านทำให้คำสั่งที่ซ่อนในไฟล์ยึดคำตอบได้จริง

**ทุก request มี `X-Request-ID` ส่งต่อทุก hop และทุก service log เป็น JSON บรรทัดเดียว**
เมื่อรวมงานแล้วเกิดปัญหา ไล่ `request_id` เดียวกันผ่าน `make logs` จะทราบทันทีว่าล้มเหลวที่ hop ใด

**`router` คืน `trace` กลับมาด้วย** บอกว่าตัดสินใจที่ชั้นไหนและใช้เวลาตรงไหนบ้าง
ข้อมูลนี้ไหลผ่านอยู่แล้วจึงไม่มีต้นทุนเพิ่ม แต่เก็บย้อนหลังไม่ได้ถ้าไม่ใส่ตั้งแต่แรก

**โมเดลกับดัชนีอยู่ใน named volume ไม่ใช่ใน image**
ไม่เช่นนั้น `build` ทุกครั้งจะโหลดใหม่เป็น GB และ image จะมีขนาดใหญ่เกินกว่าจะแชร์กันได้

**ล็อกอินใช้ผู้ใช้ตัวอย่างในฐานข้อมูล ตั้งใจไม่ทำหน้าสมัครสมาชิก**
โจทย์ของงานนี้คือตัวระบบ agentic ไม่ใช่ระบบสมาชิก · ตาราง `users` กับเส้นล็อกอิน–คุกกี้–เพดานคำถามรายบัญชีทำไว้ครบแล้ว เติมหน้าสมัครทีหลังได้โดยไม่ต้องรื้อของเดิม

---

## ข้อจำกัดที่รู้อยู่

ทุกข้อในตารางนี้ทราบตั้งแต่ตอนพัฒนา ผ่านการวัดหรือตรวจโค้ดยืนยันแล้ว และระบุแนวทางแก้ไว้หากมีเวลาทำต่อ

| เรื่อง | สภาพตอนนี้ | ถ้าจะทำต่อ |
|---|---|---|
| cross-encoder reranker | ปิดเป็นค่าเริ่มต้น วัดแล้วได้ hit@5 0.93 แต่กิน RAM รวม ~4.3 GB และเพิ่มเวลา ~15 วินาทีต่อคำถามบน CPU ล้วน | เปิดเมื่อมี GPU หรือย้ายไป reranker ตัวเล็กกว่า |
| คำถามหมวด "เลือกซื้ออุปกรณ์ / งานเอกสาร" | ไปเส้น `general_ai` ทั้งที่คลังมีคำตอบ ตอบถูกแต่ไม่มีเลขอ้างอิง — เป็นผลจากการ map หมวดใน CONTRACT ให้ผังอ่านง่าย | แยกหมวดพวกนี้กลับไป `university_rag` แล้ววัดใหม่ |
| แผงการตัดสินใจของ agent | เปิดดูได้เฉพาะแชทรอบปัจจุบัน แชทเก่ากดไม่ได้ ทั้งที่ฐานข้อมูลเก็บ `trace` ไว้ครบแล้ว | ให้ `/api/history` ส่งฟิลด์ `trace` กลับมาด้วย (แก้ ~3 บรรทัดที่ 07 และ 1 บรรทัดที่ 01) |
| ปุ่มให้คะแนนคำตอบ | ฝั่ง backend พร้อมครบ (`/api/feedback` · ตาราง `feedback` · export CSV) แต่หน้าเว็บชุดใหม่ยังไม่มีปุ่มให้กด | เติมปุ่มในหน้าแชทแล้วเรียก `/api/feedback` ที่มีอยู่แล้ว |
| อัปโหลดไฟล์ | `/api/upload` ยังเป็น stub คืน 501 และหน้าเว็บยังไม่มีปุ่มแนบไฟล์ · ของที่ทำรอไว้แล้วคือตาราง `uploaded_files` และด่านกันคำสั่งแฝงใน `engines` ซึ่งยังไม่มีไฟล์จริงให้ทำงานด้วย | ต่อ pipeline อ่านไฟล์ → เก็บข้อความ → ส่งเป็น context |
| โควตา LLM | Groq free tier จำกัดทั้งต่อนาทีและต่อวัน ถ้าใช้หนักจะถอยไปตัวสำรองเอง | ใช้ key แบบเสียเงิน หรือรัน LLM ในเครื่อง |

---

## ทำซ้ำผลวัดเอง

```bash
git clone https://github.com/pitchakorn-pkt/chuayduay.git
cd chuayduay
cp .env.example .env     # แล้วใส่ API key ของตัวเอง
make warmup              # ดึงโมเดล embedding ลง volume (ครั้งแรกบนเครื่องใหม่เท่านั้น)
make up                  # ขึ้นทั้งระบบ รอจนทุกตัว healthy
make ingest              # สร้างดัชนีค้นหาจากเอกสาร
docker compose restart retrieval   # ต้องทำทุกครั้งหลัง ingest — เหตุผลอยู่ในกล่องข้างล่าง
make smoke               # ได้ 14/14
make eval                # ได้ตัวเลขในหัวข้อ "ผลที่วัดได้" ข้อ 1
```

> [!IMPORTANT]
> **รัน `make ingest` ตอนที่ระบบขึ้นอยู่แล้ว ต้อง `docker compose restart retrieval` ตามทุกครั้ง**
> เพราะ ingest เขียนดัชนีชุดใหม่ แต่ service ที่รันค้างอยู่ยังถือดัชนีชุดเดิมที่ถูกเขียนทับไปแล้ว
> อาการนี้สังเกตได้ยาก: ระบบไม่ล่ม ผู้ใช้ยังได้คำตอบ (router ถอยไปตอบด้วยความรู้ทั่วไป) **แต่แหล่งอ้างอิงจะหายไปเงียบ ๆ**

`eval/report.html` เป็นหน้าเว็บไฟล์เดียวแบบสมบูรณ์ในตัว เปิดด้วยการดับเบิลคลิกได้โดยไม่ต้องเชื่อมต่ออินเทอร์เน็ต
ทั้ง `report.md` และ `report.html` อยู่ใน `.gitignore` เพราะเป็นผลรัน ไม่ใช่โค้ด — ตัวเลขในหน้านี้จึงต้องรันเองถึงจะได้กลับมา

ชุด 64 ข้อเรียกด้วยบัญชีเดียว จึงชนเพดานจำนวนคำถามต่อนาทีของ `api` ได้ — สคริปต์รอตามที่ระบบแจ้งแล้วเรียกซ้ำให้เอง ไม่นับเป็นข้อที่ตก
หากต้องการสงวนโควตารายวันของ Groq ไว้ ให้ตั้ง `LLM_PRIMARY=gemini` ก่อนรัน แล้วสลับกลับเมื่อเสร็จ

`smoke_test.sh` ตรวจ 14 ข้อ — `/health` ของ 6 service, ล็อกอิน, 5 คำถามให้ครบทั้ง 5 route, ประวัติ และสถิติ เป็นการตรวจว่าทั้งเส้นทางเชื่อมต่อกันได้ ไม่ใช่ชุดทดสอบเคสขอบ
เคสขอบที่เคยพังเงียบในระบบแบบนี้อยู่ใน pytest ของ 02 แทน — ขอประวัติ session ของคนอื่นต้องได้ 404 และบทสนทนายาวต้องส่งเข้า router แค่ 10 ข้อความล่าสุด · ส่วนการกด feedback ก่อนข้อความลงฐานข้อมูลทัน 07 รับไว้ด้วย upsert แล้วค่อยเชื่อมกันตอนอ่าน (ยังไม่มีเทสอัตโนมัติครอบเคสนี้)

---

## วิธีจัดการงานของทีม

8 คน 8 โมดูล **คนละหนึ่งโฟลเดอร์ คนละหนึ่ง branch** — ทุกคนแก้ได้เฉพาะ `services/<โฟลเดอร์ของตัวเอง>/` เข้า `develop` ผ่าน Pull Request เท่านั้น และ `main` รับ merge จาก `develop` อย่างเดียว เจอบั๊กในงานคนอื่นให้เปิด Issue แท็กเจ้าของ ไม่แก้แทนกัน เพื่อให้ประวัติ commit สะท้อนว่าใครทำอะไรจริง

สิ่งที่ทำให้แปดคนทำงานขนานกันได้โดยไม่ต้องรอใคร คือ [`docs/CONTRACT.md`](docs/CONTRACT.md) ที่ล็อกรูปแบบ JSON ทุกเส้นและชื่อ env ทุกตัวไว้ตั้งแต่วันแรก ทุกโมดูลจึงเขียนโค้ดเรียกหากันได้ทันทีโดยไม่ต้องทำ mock เอง และเมื่อของจริงมาแทน stub ก็ไม่มีอะไรต้องแก้ · `.github/CODEOWNERS` ผูกโฟลเดอร์กับเจ้าของไว้ GitHub จึงขอ review จากคนที่ถูกต้องให้เองทุก PR · มี webhook แจ้งเตือนเข้า Discord เมื่อเปิด / merge / ปิด PR และแจ้งทันทีเมื่อมีใครแตะ `CONTRACT.md` เพราะเป็นไฟล์เดียวที่พังแล้วกระทบทั้งทีม

หัวหน้าทีมดูแลไฟล์ที่ราก (`docker-compose*.yml`, `Makefile`, `scripts/`, `eval/`) รวมงานทุกโมดูล รีวิวทุก PR และเป็นคนรันชุดวัดผลทั้งระบบ

คำสั่งประจำวัน วิธีทำงานบน Windows และโครงของ repo อยู่ที่ [`08_monitoring_deployment/README.md`](08_monitoring_deployment/)

---

## เอกสาร

| ไฟล์ | อ่านเมื่อใด |
|---|---|
| [`docs/00_PLAN_OVERVIEW.md`](docs/00_PLAN_OVERVIEW.md) | อ่านก่อนอย่างอื่น — ภาพรวม สถาปัตยกรรม ข้อตกลงของทีม ความเสี่ยงที่ประเมินไว้ |
| [`docs/CONTRACT.md`](docs/CONTRACT.md) | **กฎสูงสุด** รูปแบบ JSON ทุกเส้น ชื่อ env ทุกตัว — เมื่อใดที่โค้ดขัดกับเอกสารนี้ ถือว่าโค้ดผิด |
| [`docs/SCHEDULE.md`](docs/SCHEDULE.md) | ใครต้องส่งอะไรวันไหน วันไหนคุณรอใคร ใครรอคุณ |
| [`docs/GIT_FLOW.md`](docs/GIT_FLOW.md) | วิธีใช้ git ของทีม — ไม่เคยใช้ git มาก่อน อ่านเฉพาะหัวข้อ 0 ถึง 4 ก็เพียงพอ |
| [`08_monitoring_deployment/README.md`](08_monitoring_deployment/) | คำสั่งที่ใช้บ่อย คู่มือสำหรับทีม ทำงานบน Windows โครงของ repo |

รายละเอียดงานของแต่ละคนอยู่ในไฟล์ที่ปักหมุดในห้อง Discord ของโมดูลนั้น
