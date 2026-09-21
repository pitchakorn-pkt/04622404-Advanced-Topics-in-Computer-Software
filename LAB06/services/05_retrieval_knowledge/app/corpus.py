"""โหลดเอกสารจาก data/raw/ แล้วประกอบเป็น Document พร้อม paragraph ที่พร้อม chunk

สองแหล่งข้อมูลตาม docs/team/05_retrieval_knowledge.md
  1. it_support: daily_tech_qa.txt — 194 คู่ถาม-ตอบ 10 หมวดไทย
     * รวมคู่ถาม-ตอบหมวดเดียวกันเป็นเอกสารเดียวก่อน chunk (ไม่งั้น chunk ไม่ทำงาน)
     * เก็บ source_qa_index (ตำแหน่ง 0-based ของคู่นั้นในไฟล์ต้นฉบับ เรียงทั้งไฟล์) ไว้ต่อ paragraph
       เพื่อย้อนกลับไปหา relevant_chunk_ids ของ golden set ได้
  2. howto: บทความยาวจาก 04/07 ใน data/raw/howto/*.md (ยังไม่มีไฟล์ก็ไม่เป็นไร ข้ามเงียบ ๆ)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from .text_processing import Paragraph, clean_text

QA_FILE = "daily_tech_qa.txt"
HOWTO_DIRNAME = "howto"

# หมวดไทย -> slug อังกฤษสั้น ๆ ใช้ทำ doc_id อ่านง่าย (เลขคู่ถาม-ตอบผูกกับ metadata ไม่ใช่กับ slug นี้)
CATEGORY_SLUG = {
    "แบตเตอรี่และการชาร์จ": "battery",
    "เครื่องช้าและพื้นที่เต็ม": "performance",
    "อินเทอร์เน็ตและไวไฟ": "connectivity",
    "บัญชีและรหัสผ่าน": "account",
    "มิจฉาชีพและความปลอดภัย": "security",
    "ข้อมูลและการสำรอง": "backup",
    "แอปและการอัปเดต": "apps",
    "หน้าจอ เสียง และกล้อง": "hardware",
    "การเลือกซื้อและดูแลเครื่อง": "buying-care",
    "การใช้งานเอกสารและงานทั่วไป": "office",
}

# วันที่รวบรวมคลังหลัก ไม่มีวันที่จริงต่อคู่ถาม-ตอบในไฟล์ต้นฉบับ ใช้ค่าคงที่นี้แทนทั้งคลัง
IT_SUPPORT_DATE = "2026-01-15"

QA_PAIR_RE = re.compile(r"Q:\s*(.+?)\s*\nA:\s*(.+?)\s*(?=\n\n|\nQ:|\Z)", re.S)
CATEGORY_SPLIT_RE = re.compile(r"\[หมวด:\s*(.*?)\s*\]")

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.S)


@dataclass
class Document:
    doc_id: str
    title: str
    url: str | None
    date: str | None
    category: str  # ค่าตาม CONTRACT: it_support | howto | faq | policy | other
    category_th: str | None
    status: str
    file: str
    paragraphs: list[Paragraph] = field(default_factory=list)


def load_it_support(raw_dir: str) -> list[Document]:
    path = os.path.join(raw_dir, QA_FILE)
    if not os.path.exists(path):
        return []
    raw = open(path, encoding="utf-8").read()

    pairs: list[tuple[int, str, str, str]] = []  # (global_index, category_th, question, answer)
    parts = CATEGORY_SPLIT_RE.split(raw)
    idx = 0
    for i in range(1, len(parts), 2):
        category_th = parts[i]
        block = parts[i + 1]
        for m in QA_PAIR_RE.finditer(block):
            question, answer = clean_text(m.group(1)), clean_text(m.group(2))
            pairs.append((idx, category_th, question, answer))
            idx += 1

    by_category: dict[str, list[tuple[int, str, str]]] = {}
    for global_index, category_th, question, answer in pairs:
        by_category.setdefault(category_th, []).append((global_index, question, answer))

    docs: list[Document] = []
    for category_th, items in by_category.items():
        slug = CATEGORY_SLUG.get(category_th, re.sub(r"\W+", "-", category_th).strip("-").lower())
        doc_id = f"it-{slug}"
        paragraphs = [
            Paragraph(text=f"Q: {q}\nA: {a}", source_qa_index=gi, page=1)
            for gi, q, a in items
        ]
        docs.append(Document(
            doc_id=doc_id,
            title=f"คำถามที่พบบ่อย: {category_th}",
            url=f"internal://daily_tech_qa/{slug}",
            date=IT_SUPPORT_DATE,
            category="it_support",
            category_th=category_th,
            status="active",
            file=os.path.relpath(path, raw_dir).replace(os.sep, "/"),
            paragraphs=paragraphs,
        ))
    return docs


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip()
            if v:  # "url:" ว่าง ๆ ต้องเป็น None ไม่ใช่ "" (Source.url เป็น str | None)
                meta[k.strip()] = v
    return meta, m.group(2)


def load_howto(raw_dir: str) -> list[Document]:
    howto_dir = os.path.join(raw_dir, HOWTO_DIRNAME)
    if not os.path.isdir(howto_dir):
        return []
    docs: list[Document] = []
    for name in sorted(os.listdir(howto_dir)):
        if not name.endswith((".md", ".txt")):
            continue
        path = os.path.join(howto_dir, name)
        raw = clean_text(open(path, encoding="utf-8").read())
        meta, body = _parse_frontmatter(raw)
        doc_id = meta.get("doc_id") or f"howto-{os.path.splitext(name)[0]}"
        title = meta.get("title") or os.path.splitext(name)[0]
        paras = [clean_text(p) for p in re.split(r"\n\s*\n", body) if clean_text(p)]
        docs.append(Document(
            doc_id=doc_id,
            title=title,
            url=meta.get("url"),
            date=meta.get("date"),
            category="howto",
            category_th=None,
            status=meta.get("status", "active"),
            file=os.path.relpath(path, raw_dir).replace(os.sep, "/"),
            paragraphs=[Paragraph(text=p) for p in paras],
        ))
    return docs


def load_all_documents(raw_dir: str) -> list[Document]:
    return load_it_support(raw_dir) + load_howto(raw_dir)


def write_manifest(docs: list[Document], manifest_path: str) -> None:
    import csv
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["doc_id", "title", "url", "date", "category", "status", "file"])
        for d in docs:
            writer.writerow([d.doc_id, d.title, d.url or "", d.date or "", d.category, d.status, d.file])
