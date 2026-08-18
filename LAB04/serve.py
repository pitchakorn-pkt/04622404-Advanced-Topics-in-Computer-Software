# เปิดหน้าเว็บถาม-ตอบของระบบ RAG ตัวเดียวกับ main.py
#
# 1. สร้าง index ก่อน: python build_index.py
# 2. ตั้งคีย์ LLM:     export GROQ_API_KEY=...
# 3. รัน:              python serve.py   แล้วเปิด http://127.0.0.1:8000
#
# โหลดโมเดลครั้งเดียวตอนเปิดเซิร์ฟเวอร์ ไม่ใช่ทุกคำถาม

import json
import os
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

import config
from src import index_meta
from src.generator import NoLLM
from src.rag_pipeline import RAGPipeline

HOST = "127.0.0.1"
PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

rag = None      # สร้างใน main() หลังตรวจ index แล้ว

# ต่ำกว่านี้ถือว่าคลังไม่มีเรื่องนี้ — ใช้ cosine ของ chunk ที่ใกล้คำถามที่สุด
#
# วัดจากคำถามจริง 60 ข้อ (data/eval_paraphrases.txt) กับคำถามนอกคลังที่เขียนขึ้น 20 ข้อ
#   คำถามจริง   : ต่ำสุด 0.5071 · มัธยฐาน 0.6469
#   นอกคลัง     : 13 ใน 20 ข้ออยู่ต่ำกว่า 0.50
# ที่เกณฑ์ 0.50 จึงไม่ปฏิเสธคำถามจริงผิดสักข้อ (0/60)
#
# ใช้คะแนน dense ไม่ใช่คะแนน rerank เพราะ cross-encoder ให้คะแนนเชิงจัดอันดับ
# ไม่ใช่ความน่าจะเป็นที่สอบเทียบแล้ว — มันให้ "ช่วยหน่อย" ถึง 0.8161 และ "hello" 0.7271
RELEVANCE_MIN = 0.50

GENERAL_PROMPT = """คุณคือผู้ช่วยตอบคำถามทั่วไป ตอบเป็นภาษาไทย

กฎ:
1. ตอบสั้น ๆ ไม่เกิน 4 ประโยค
2. ถ้าไม่แน่ใจให้บอกว่าไม่แน่ใจ ห้ามแต่งตัวเลข ราคา หรือรายละเอียดที่ไม่มั่นใจ
3. ถ้าเป็นคำทักทายหรือข้อความที่ไม่ใช่คำถาม ให้ทักทายกลับสั้น ๆ แล้วบอกว่าถามเรื่องมือถือหรือคอมพิวเตอร์ได้"""


# คอนฟิกการค้นที่สลับได้จากหน้าเว็บ ตรงกับ 3 แถวในตารางผลการวัดของ README
MODES = {
    "dense":  {"hybrid": False, "rerank": False},
    "hybrid": {"hybrid": True,  "rerank": False},
    "full":   {"hybrid": True,  "rerank": True},
}


@contextmanager
def retrieval_mode(name):
    """
    สลับคอนฟิกการค้นชั่วคราวเฉพาะคำถามนี้ แล้วคืนค่าเดิมเสมอ

    config.USE_HYBRID ถูกอ่านตอนเรียก retrieve() จึงเปลี่ยนกลางคันได้
    ส่วน rerank ดูจาก retriever.reranker ว่าเป็น None หรือไม่
    ค่าที่เปลี่ยนอยู่ในหน่วยความจำของโปรเซสนี้เท่านั้น ไม่ได้เขียนทับ config.py
    เซิร์ฟเวอร์รับทีละคำขอ จึงไม่มีคำถามสองข้อมาแย่งค่ากัน
    """
    setting  = MODES[name]
    hybrid   = config.USE_HYBRID
    reranker = rag.retriever.reranker

    config.USE_HYBRID = setting["hybrid"]
    if not setting["rerank"]:
        rag.retriever.reranker = None

    try:
        yield
    finally:
        config.USE_HYBRID = hybrid
        rag.retriever.reranker = reranker


def corpus_relevance(question):
    """cosine ของ chunk ที่ใกล้คำถามที่สุด — บอกว่าคลังมีเรื่องนี้อยู่หรือเปล่า"""
    query = rag.transformer.transform(question)[0]
    hits = rag.retriever.dense_search(query, 1)
    return float(hits[0][1]) if hits else 0.0


def answer_outside_corpus(question):
    """
    คำถามที่คลังไม่มี — ให้ LLM ตอบจากความรู้ของตัวเอง โดยไม่ส่ง context ไปเลย

    แยกออกมาเป็นคนละทางกับคำตอบที่มีแหล่งอ้างอิง เพื่อให้หน้าเว็บติดป้ายได้ชัด
    ว่าประโยคไหนตรวจย้อนกลับไปที่คลังได้ ประโยคไหนไม่ได้
    """
    llm = rag.generator.llm

    if isinstance(llm, NoLLM):
        return None     # ไม่มี key ก็ไม่มีความรู้ทั่วไปให้ใช้

    messages = [
        {"role": "system", "content": GENERAL_PROMPT},
        {"role": "user", "content": question},
    ]

    try:
        return llm.chat(messages)
    except Exception as error:
        return f"เรียก LLM ไม่สำเร็จ: {error}"


def ranking_before_rerank(question):
    """
    อันดับที่ RRF ให้มา ก่อนที่ cross-encoder จะจัดใหม่

    ค้นซ้ำอีกรอบโดยปิด rerank แล้วขอผู้เข้ารอบเท่า CANDIDATE_K
    ซึ่งคือชุดเดียวกับที่ rerank ได้รับไปจัดอันดับ ใช้เทียบว่าขั้นนี้ทำอะไรบ้าง
    """
    with retrieval_mode("hybrid"):
        query = rag.transformer.transform(question)[0]
        chunks = rag.retriever.retrieve(query, top_k=config.CANDIDATE_K)

    return [
        {
            "rank": rank,
            "chunk_id": chunk["chunk_id"],
            "question": chunk["question"],
            "score": round(float(chunk["score"]), 5),
        }
        for rank, chunk in enumerate(chunks, start=1)
    ]


def answer_question(question, mode):
    """ถาม 1 คำถาม แล้วจัดรูปผลลัพธ์ให้หน้าเว็บใช้ได้"""
    started = time.time()
    relevance = corpus_relevance(question)

    # คลังไม่มีเรื่องนี้ — ไม่ต้องค้นต่อ ไม่ต้องแกล้งตอบด้วย chunk ที่ไม่เกี่ยว
    if relevance < RELEVANCE_MIN:
        outside = answer_outside_corpus(question)

        if config.USE_MEMORY and outside:
            rag.memory.add_user(question)
            rag.memory.add_assistant(outside)

        return {
            "answer": config.NO_CONTEXT_MESSAGE,
            "outside": outside,
            "relevance": round(relevance, 4),
            "sources": [],
            "before": [],
            "timings": {"รวม": round(time.time() - started, 2)},
            "no_context": True,
            "mode": mode,
        }

    with retrieval_mode(mode):
        result = rag.ask(question)

    # เทียบอันดับก่อน-หลัง rerank ได้เฉพาะตอนที่ขั้นนี้ทำงานจริง
    before = ranking_before_rerank(question) if MODES[mode]["rerank"] else []
    ranks = {row["chunk_id"]: row["rank"] for row in before}

    # sources บอกแค่คำถามกับเลขบรรทัด เติมเนื้อคำตอบกับคะแนนของแต่ละขั้นเข้าไปด้วย
    found = {chunk["chunk_id"]: chunk for chunk in result["retrieved"]}

    sources = []
    for source in result["sources"]:
        chunk = found.get(source["chunk_id"], {})
        sources.append(dict(
            source,
            answer=chunk.get("answer", ""),
            dense=chunk.get("dense_score"),
            bm25=chunk.get("bm25_score"),
            rrf=chunk.get("retrieval_score"),   # คะแนนก่อน rerank (มีเมื่อ rerank ทำงาน)
            rank_before=ranks.get(source["chunk_id"]),
        ))

    return {
        "answer": result["answer"],
        "sources": sources,
        "timings": result["timings"],
        "no_context": result["no_context"],
        "mode": mode,
        "before": before,
        "outside": None,
        "relevance": round(relevance, 4),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_file("index.html", "text/html; charset=utf-8")
        elif self.path == "/settings":
            self.send_json({
                "corpus": os.path.basename(config.SOURCE_FILE),
                "embedding": config.EMBEDDING_MODEL_NAME,
                "rerank": config.RERANK_MODEL_NAME if config.USE_RERANK else "",
                "llm": f"{config.LLM_PROVIDER} · {config.LLM_MODEL or config.LLM_PROVIDERS[config.LLM_PROVIDER][1]}" if config.USE_LLM else "ปิด",
                "weights": f"dense {config.DENSE_WEIGHT} : BM25 {config.BM25_WEIGHT}",
                "top_k": config.TOP_K,
                "chunks": len(rag.retriever.chunks),
            })
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/ask":
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))

            question = payload.get("question", "").strip()
            mode = payload.get("mode", "full")

            if not question:
                self.send_json({"error": "ไม่ได้ส่งคำถามมา"}, status=400)
                return

            if mode not in MODES:
                self.send_json({"error": f"ไม่รู้จักโหมด {mode}"}, status=400)
                return

            try:
                self.send_json(answer_question(question, mode))
            except Exception as error:
                self.send_json({"error": str(error)}, status=500)

        elif self.path == "/reset":
            rag.reset()
            self.send_json({"ok": True})
        else:
            self.send_error(404)

    def send_file(self, name, content_type):
        with open(os.path.join(WEB_DIR, name), "rb") as file:
            body = file.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass    # ไม่ต้องพ่น log ทุก request ตอนนำเสนอ


def main():
    global rag

    if not os.path.exists(config.FAISS_INDEX_FILE):
        print("ไม่พบ FAISS index — รัน: python build_index.py")
        return

    index_meta.warn_if_stale()

    print("กำลังโหลดโมเดล (ครั้งแรกอาจนาน) ...")
    rag = RAGPipeline()

    print(f"\nพร้อมแล้ว → http://{HOST}:{PORT}   (Ctrl+C เพื่อหยุด)")
    HTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
