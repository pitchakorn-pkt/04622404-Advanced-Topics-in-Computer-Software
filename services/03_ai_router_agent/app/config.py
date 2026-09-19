"""ค่าคงที่และ env ทั้งหมดของ router รวมไว้ที่เดียว

ชื่อ env ทุกตัวมาจาก docs/CONTRACT.md ข้อ 7 — ห้ามตั้งชื่อใหม่เอง
timeout ต่อ hop มาจาก CONTRACT ข้อ 0 (เป็น "เพดานต่อ hop" ไม่ใช่งบรวม)
งบรวมทั้ง request คุมด้วย app/budget.py
"""
from __future__ import annotations

import os

# ---- ปลายทางที่เราเรียก (ห้าม hardcode localhost — แต่ละ container มี localhost ของตัวเอง) ----
ENGINES_URL = os.getenv("ENGINES_URL", "http://engines:8000")
RETRIEVAL_URL = os.getenv("RETRIEVAL_URL", "http://retrieval:8000")
GENERATION_URL = os.getenv("GENERATION_URL", "http://generation:8000")

# ---- เพดานเวลาต่อ hop ตาม CONTRACT ข้อ 0 ----
T_ENGINES = 30.0
T_RETRIEVAL = 15.0
T_GENERATION = 30.0
# LLM ที่ router เรียกเอง (ชั้น 3 และ rewrite) ไม่อยู่ในตาราง hop เพราะไม่ใช่ service ของทีม
# CONTRACT ข้อ 0 กำหนดไว้ว่าต้อง <= 10s และนับรวมในงบ 70s
T_LLM = 10.0

# ---- งบเวลารวมของทั้ง request ----
# api รอเราไว้ 75s เราต้องจบก่อนที่ 70s ไม่งั้นผู้ใช้เห็น 504 ทั้งที่ทุกอย่างกำลังจะสำเร็จ
TOTAL_BUDGET = float(os.getenv("ROUTER_TOTAL_BUDGET", "70"))
MIN_HOP = 1.5    # เหลือน้อยกว่านี้ไม่ต้องเริ่ม hop ใหม่ ตอบเท่าที่มีดีกว่าโดนตัดสาย
RESERVE = 1.0    # กันไว้ประกอบคำตอบและเขียน log

# ---- เกณฑ์ตัดสินใจ ----
CLASSIFIER_THRESHOLD = 0.75   # CONTRACT ข้อ 3: ต่ำกว่านี้ให้ตกไปชั้น 3
RULES_CONFIDENCE = 0.9        # CONTRACT ข้อ 0: ชั้น rules คงที่ที่ 0.9
LLM_MIN_CONFIDENCE = 0.5      # ต่ำกว่านี้ถามกลับ ดีกว่าเดาแล้วพาไปผิดเส้น
TOP_K = 5

# ---- ขนาด context ----
HISTORY_MAX_MESSAGES = 10     # CONTRACT ข้อ 2: api ส่งมาไม่เกิน 10 อยู่แล้ว เราเผื่อไว้อีกชั้น
HISTORY_MAX_CHARS = 6000

# ---- ตาราง map หมวด -> route (CONTRACT ข้อ 3 ล็อกแล้ว ห้ามตีความเอง) ----
CATEGORY_ROUTE = {
    "connectivity": "university_rag",
    "account_security": "university_rag",
    "device_performance": "university_rag",
    "data_backup": "university_rag",
    "apps_updates": "university_rag",
    "hardware_media": "university_rag",
    "general_other": "general_ai",
    "out_of_scope": "decline",
}

# ---- LLM: หนึ่งไลบรารี สลับเจ้าด้วย base_url (CONTRACT ข้อ 7) ----
# ห้าม hardcode ชื่อโมเดล — Groq ถอดโมเดลออกโดยไม่แจ้งมาแล้ว อ่านจาก env เสมอ
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
    },
}

LLM_PRIMARY = os.getenv("LLM_PRIMARY", "groq")
LLM_FALLBACK = os.getenv("LLM_FALLBACK", "gemini")


def provider_config(name: str) -> dict:
    """อ่าน key/model จาก env ตอนเรียกใช้ ไม่ใช่ตอน import — แก้ .env แล้ว restart ก็เห็นค่าใหม่"""
    cfg = PROVIDERS.get(name)
    if not cfg:
        return {}
    return {
        "provider": name,
        "base_url": cfg["base_url"],
        "api_key": os.getenv(cfg["api_key_env"], ""),
        "model": os.getenv(cfg["model_env"], ""),
    }
