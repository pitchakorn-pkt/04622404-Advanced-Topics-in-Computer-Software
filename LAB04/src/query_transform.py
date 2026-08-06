# query_transform.py
# Improve user queries before retrieval.
#
# Problem
# Retrieval quality depends on the user's query. Real users often write
# short or ambiguous questions, or mix Thai transliteration with English terms.
#
#     "wifi ต่อไม่ติด"           ← user types the English form
#     Knowledge base: "ไวไฟ"      ← BM25 sees these as unrelated tokens
#
#     "อัพเดทแล้วเครื่องช้า"      ← common Thai misspelling of อัปเดต
#
#     "แล้วอันไหนดีกว่ากัน"       ← unclear without context
#
# Since the knowledge base uses Thai transliterations and the correct spelling,
# query transformation helps bridge the gap between user language and stored documents.
#
# Two levels are available:
#
# Level 1 — normalize_query()
#     No AI required. Replaces slang using a lookup table.
#     Fast, free, and always enabled.
#
# Level 2 — transform()
#     Uses an LLM when config.USE_QUERY_TRANSFORM is enabled.
#
#     rewrite
#         Rewrite the query into a clearer question.
#
#     multi_query
#         Generate multiple equivalent queries and search all of them.
#
#     hyde
#         Generate a hypothetical answer and use it as the search query.
#         This works because answer-like text is often closer to the
#         correct document than the original question.

import re

import config
from src.prompt_templates import HYDE_PROMPT, MULTI_QUERY_PROMPT, REWRITE_PROMPT

# ตารางแทนคำพูดทั่วไปด้วยศัพท์ที่ใช้จริงในเอกสาร — เพิ่มคำได้ตามต้องการ ไม่ต้องแก้โค้ดส่วนอื่น
#
# โดเมนนี้มีปัญหาเฉพาะตัวคือ "คำเดียวกันเขียนได้สองระบบตัวอักษร" ผู้ใช้พิมพ์ทับศัพท์ไทย
# ว่า "ไวไฟ" แต่ในคลังเขียนว่า "Wi-Fi" ซึ่ง BM25 มองเป็นคนละคำโดยสิ้นเชิง
# การแมปตรงนี้จึงเป็นตัวอุดช่องว่างข้ามระบบตัวอักษรก่อนถึงขั้นค้นหา
SLANG_MAP = {
    # คำอังกฤษที่คนพิมพ์ แต่ในคลังเขียนเป็นคำทับศัพท์ไทย
    "Wi-Fi": "ไวไฟ",
    "WiFi": "ไวไฟ",
    "wifi": "ไวไฟ",
    "Bluetooth": "บลูทูธ",
    "bluetooth": "บลูทูธ",
    "cloud": "คลาวด์",
    "OTP": "โอทีพี",
    "otp": "โอทีพี",
    "app": "แอป",
    "backup": "สำรองข้อมูล",
    "password": "รหัสผ่าน",
    # คำไทยที่คนสะกดผิดกันประจำ
    "อัพเดท": "อัปเดต",
    "อัพเดต": "อัปเดต",
    "โน๊ตบุ๊ค": "โน้ตบุ๊ก",
    "โน๊ตบุ้ค": "โน้ตบุ๊ก",
    "รีสตาร์ท": "รีสตาร์ต",
    "เน็ท": "เน็ต",
    "แบตเตอรี": "แบตเตอรี่",
}

# คำลงท้ายที่ไม่ช่วยในการค้นหา
ENDING_WORDS = re.compile(r"\s*(ครับ|ค่ะ|คะ|จ้า|น้า|หน่อย)\s*$")


def normalize_query(query):
    """
    ปรับคำถามแบบไม่ใช้ AI — เร็วและฟรี

        "เป็นแผลที่น้องชายครับ"  →  "เป็นแผลที่อวัยวะเพศชาย"
    """
    text = re.sub(r"\s+", " ", query).strip()       # ตัดช่องว่างซ้ำซ้อน

    for slang, formal in SLANG_MAP.items():
        text = text.replace(slang, formal)

    text = ENDING_WORDS.sub("", text)
    return text.strip() or query.strip()            # ถ้าตัดจนหมด ใช้ของเดิม


def clean_line(line):
    """ตัดเลขข้อ เครื่องหมายคำพูด และคำนำหน้า ที่ LLM ชอบใส่มาให้"""
    text = line.strip()
    text = re.sub(r"^\s*(\d+[\.\)]|[-*•])\s*", "", text)    # "1. " หรือ "- "
    text = re.sub(r"^(คำถาม|คำค้นหา|Query)\s*[:：]\s*", "", text)
    return text.strip().strip('"').strip("'")


class QueryTransformer:
    def __init__(self, llm):
        self.llm = llm

    def ask_llm(self, prompt):
        return self.llm.chat([{"role": "user", "content": prompt}])

    def rewrite(self, query, history):
        """ให้ LLM เขียนคำถามใหม่ให้ชัดเจนและสมบูรณ์ในตัวเอง"""
        history_block = f"บทสนทนาก่อนหน้า:\n{history}\n\n" if history else ""
        prompt = REWRITE_PROMPT.format(history=history_block, question=query)
        return [clean_line(self.ask_llm(prompt))]

    def multi_query(self, query):
        """ให้ LLM แต่งคำถามที่ความหมายเดียวกันหลายแบบ"""
        prompt = MULTI_QUERY_PROMPT.format(n=config.MULTI_QUERY_COUNT, question=query)
        answer = self.ask_llm(prompt)

        queries = [normalize_query(query)]           # เก็บคำถามเดิมไว้เป็นตัวแรก
        for line in answer.splitlines():
            new_query = clean_line(line)
            if new_query and new_query not in queries:
                queries.append(new_query)

        return queries[: config.MULTI_QUERY_COUNT + 1]

    def hyde(self, query):
        """ให้ LLM แต่งคำตอบสมมติ แล้วใช้คำตอบนั้นเป็นคำค้นด้วย"""
        fake_answer = self.ask_llm(HYDE_PROMPT.format(question=query)).strip()

        # เก็บคำถามเดิมไว้ด้วย เผื่อคำตอบสมมติหลุดประเด็น
        return [normalize_query(query), fake_answer]

    def transform(self, query, history=""):
        """
        คืน list ของคำถามที่จะเอาไปค้น — อย่างน้อย 1 ข้อเสมอ

        ถ้า LLM ใช้ไม่ได้ จะคืนคำถามเดิม การค้นหาจึงไม่พังเพราะขั้นนี้
        """
        if not config.USE_QUERY_TRANSFORM:
            return [normalize_query(query)]

        try:
            if config.QUERY_TRANSFORM_MODE == "rewrite":
                return self.rewrite(query, history)
            if config.QUERY_TRANSFORM_MODE == "hyde":
                return self.hyde(query)
            return self.multi_query(query)

        except Exception as error:
            print(f"[query_transform] ล้มเหลว ({error}) — ใช้คำถามเดิม")
            return [normalize_query(query)]


