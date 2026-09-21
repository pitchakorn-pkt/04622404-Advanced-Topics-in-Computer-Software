"""สร้างดัชนีค้นหาจากเอกสารใน data/raw — รันด้วย `make ingest` (หรือ `python ingest.py` ตรง ๆ)

ลำดับ: extract -> clean -> รวมคู่ถาม-ตอบหมวดเดียวกันเป็นเอกสาร -> chunk -> embed -> เขียนลง INDEX_DIR
เก็บ source_qa_index ต่อ chunk ไว้ตั้งแต่ขั้น chunk เพื่อ map relevant_chunk_ids ของ golden set กลับได้ทีหลัง
(ดู eval_retrieval.py)
"""
from __future__ import annotations

import sys

from app import config, embeddings
from app.corpus import load_all_documents, write_manifest
from app.index_store import ChunkRecord, save_index
from app.text_processing import chunk_paragraphs


def build_records() -> list[ChunkRecord]:
    docs = load_all_documents(config.RAW_DIR)
    if not docs:
        print(f"[ingest] ไม่พบเอกสารใน {config.RAW_DIR} — ใส่ {config.RAW_DIR}/daily_tech_qa.txt ก่อน")
        return []

    write_manifest(docs, config.MANIFEST_PATH)
    print(f"[ingest] เขียน manifest {len(docs)} เอกสารที่ {config.MANIFEST_PATH}")

    records: list[ChunkRecord] = []
    for doc in docs:
        pieces = chunk_paragraphs(doc.paragraphs, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        for i, piece in enumerate(pieces, start=1):
            records.append(ChunkRecord(
                chunk_id=f"{doc.doc_id}#p{piece.page or 1}#c{i}",
                text=piece.text,
                doc_id=doc.doc_id,
                title=doc.title,
                url=doc.url,
                date=doc.date,
                category=doc.category,
                category_th=doc.category_th,
                page=piece.page,
                source_qa_indices=piece.source_qa_indices,
            ))
        print(f"[ingest]   {doc.doc_id}: {len(doc.paragraphs)} ย่อหน้า -> {len(pieces)} chunk")
    return records


def main() -> int:
    records = build_records()
    if not records:
        print("[ingest] ไม่มี chunk ให้ index เลย — หยุดโดยไม่เขียนดัชนี")
        return 1

    print(f"[ingest] รวม {len(records)} chunk — เริ่มฝังเวกเตอร์ด้วย {config.EMBEDDING_MODEL} (อาจใช้เวลานาทีแรก)")
    vectors = embeddings.embed_passages([r.text for r in records])

    print("[ingest] สร้าง BM25 index (ตัดคำไทยด้วย pythainlp)")
    from rank_bm25 import BM25Okapi
    from app.text_processing import segment_thai
    tokenized = [segment_thai(r.text) for r in records]
    bm25 = BM25Okapi(tokenized)

    save_index(records, bm25, vectors)
    print(f"[ingest] เขียนดัชนีเสร็จที่ {config.INDEX_DIR} ({len(records)} chunk, โมเดล {config.EMBEDDING_MODEL})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
