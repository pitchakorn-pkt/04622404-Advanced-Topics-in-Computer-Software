"""อ่าน/เขียนดัชนีสองตัวที่ INDEX_DIR: BM25 (pickle) + Chroma (persistent)
เก็บ metadata ต่อ chunk (chunk_id, text, source, category_th, source_qa_index) คู่กับทั้งสองดัชนี
"""
from __future__ import annotations

import json
import os
import pickle
import time
from dataclasses import asdict, dataclass, field

from . import config


@dataclass
class ChunkRecord:
    chunk_id: str
    text: str
    doc_id: str
    title: str
    url: str | None
    date: str | None
    category: str
    category_th: str | None
    page: int | None
    source_qa_indices: list[int] = field(default_factory=list)


def save_index(records: list[ChunkRecord], bm25_obj, embeddings) -> None:
    os.makedirs(config.INDEX_DIR, exist_ok=True)

    with open(config.BM25_INDEX_PATH, "wb") as f:
        pickle.dump({"bm25": bm25_obj, "records": [asdict(r) for r in records]}, f)

    import chromadb
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    try:
        client.delete_collection(config.CHROMA_COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(config.CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[r.chunk_id for r in records],
        embeddings=[e.tolist() for e in embeddings],
        documents=[r.text for r in records],
        metadatas=[{
            "doc_id": r.doc_id, "title": r.title, "url": r.url or "", "date": r.date or "",
            "category": r.category, "category_th": r.category_th or "",
            "page": r.page or 0, "source_qa_indices": json.dumps(r.source_qa_indices),
        } for r in records],
    )

    with open(config.INDEX_META_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "embedding_model": config.EMBEDDING_MODEL,
            "chunk_count": len(records),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }, f, ensure_ascii=False, indent=2)


def load_index_meta() -> dict | None:
    if not os.path.exists(config.INDEX_META_PATH):
        return None
    with open(config.INDEX_META_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_bm25() -> tuple[object, list[ChunkRecord]] | None:
    if not os.path.exists(config.BM25_INDEX_PATH):
        return None
    with open(config.BM25_INDEX_PATH, "rb") as f:
        data = pickle.load(f)
    records = [ChunkRecord(**r) for r in data["records"]]
    return data["bm25"], records


def load_chroma_collection():
    if not os.path.isdir(config.CHROMA_DIR):
        return None
    import chromadb
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    try:
        return client.get_collection(config.CHROMA_COLLECTION)
    except Exception:
        return None
