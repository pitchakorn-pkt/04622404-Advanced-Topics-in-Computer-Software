"""ทำความสะอาดข้อความไทย ตัดคำ และแบ่ง chunk

กฎจาก docs/team/05_retrieval_knowledge.md ที่ต้องคุมในไฟล์นี้
  - ห้ามใช้ tiktoken นับความยาวข้อความไทย (ตัวเลขจะเพี้ยน) ใช้จำนวนตัวอักษรแทน
  - ตัดตามย่อหน้า/หัวข้อก่อน แล้วค่อยตัดตามความยาว ~800-1200 ตัวอักษร overlap ~150
  - ตัดคำด้วย pythainlp ตัวเดียวกันทั้งตอน index และตอน query ไม่งั้น BM25 ใช้ไม่ได้
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from pythainlp.tokenize import word_tokenize

_WS_RE = re.compile(r"[ \t ]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
# สระ/วรรณยุกต์ลอยที่ไม่ติดพยัญชนะ (มักเกิดจาก PDF extract พลาด) ตัดทิ้งถ้าอยู่ต้นบรรทัด/หลังช่องว่าง
_STRAY_TONE_RE = re.compile(r"(?<=\s)[่-๎](?=\s|$)")


def clean_text(text: str) -> str:
    """ล้าง header/footer ซ้ำที่ตรวจจับได้ง่าย ช่องว่างเกิน และสระลอยที่หลุดจาก PDF"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _STRAY_TONE_RE.sub("", text)
    text = _WS_RE.sub(" ", text)
    lines = [ln.strip() for ln in text.split("\n")]
    # ตัดบรรทัดซ้ำติดกัน (หัว/ท้ายกระดาษที่ extract มาซ้ำทุกหน้า)
    deduped: list[str] = []
    for ln in lines:
        if ln and deduped and deduped[-1] == ln:
            continue
        deduped.append(ln)
    text = "\n".join(deduped)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def segment_thai(text: str) -> list[str]:
    """ตัดคำภาษาไทยด้วย pythainlp — ใช้ฟังก์ชันนี้ทั้งตอน index และตอน query เท่านั้น"""
    tokens = word_tokenize(text, engine="newmm", keep_whitespace=False)
    return [t.strip() for t in tokens if t.strip()]


@dataclass
class Paragraph:
    text: str
    source_qa_index: int | None = None
    page: int | None = None


@dataclass
class ChunkPiece:
    text: str
    source_qa_indices: list[int] = field(default_factory=list)
    page: int | None = None


def _split_long_paragraph(p: Paragraph, size: int, overlap: int) -> list[Paragraph]:
    """ย่อหน้าเดี่ยวที่ยาวเกิน chunk size (เช่น บทความ howto) ตัดด้วยความยาวตัวอักษรแบบ sliding window"""
    text = p.text
    if len(text) <= size:
        return [p]
    pieces: list[Paragraph] = []
    step = max(size - overlap, 1)
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        pieces.append(Paragraph(text=text[start:end], source_qa_index=p.source_qa_index, page=p.page))
        if end == len(text):
            break
        start += step
    return pieces


def chunk_paragraphs(paragraphs: list[Paragraph], size: int, overlap: int) -> list[ChunkPiece]:
    """รวมย่อหน้า (แต่ละย่อหน้า = หนึ่งคู่ถาม-ตอบ หรือหนึ่งย่อหน้าของบทความ) ให้ได้ chunk ยาว ~size ตัวอักษร
    พร้อม overlap ~overlap ตัวอักษรระหว่าง chunk ติดกัน โดยยึดขอบย่อหน้าเป็นหลัก ไม่ตัดกลางประโยค
    """
    expanded: list[Paragraph] = []
    for p in paragraphs:
        expanded.extend(_split_long_paragraph(p, size, overlap))

    chunks: list[ChunkPiece] = []
    current: list[Paragraph] = []
    current_len = 0

    def flush():
        if not current:
            return
        text = "\n\n".join(p.text for p in current)
        indices = sorted({p.source_qa_index for p in current if p.source_qa_index is not None})
        pages = [p.page for p in current if p.page is not None]
        chunks.append(ChunkPiece(text=text, source_qa_indices=indices, page=pages[0] if pages else None))

    for p in expanded:
        piece_len = len(p.text) + (2 if current else 0)
        if current and current_len + piece_len > size:
            flush()
            # overlap: เอาย่อหน้าท้าย ๆ ของ chunk ก่อนหน้ามาต่อเป็นหัวของ chunk ใหม่
            carry: list[Paragraph] = []
            carry_len = 0
            for prev in reversed(current):
                if carry_len + len(prev.text) > overlap:
                    break
                carry.insert(0, prev)
                carry_len += len(prev.text)
            current = carry
            current_len = sum(len(x.text) for x in current) + 2 * max(len(current) - 1, 0)
        current.append(p)
        current_len += piece_len
    flush()
    return chunks
