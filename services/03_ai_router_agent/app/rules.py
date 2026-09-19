"""ชั้น 1 ของ cascade — ตาราง rule base ที่ล็อกแล้ว

ชื่อหมวดตรงกับ classifier ของโมดูล 04 เป๊ะ (CONTRACT ข้อ 3) เพื่อให้สถิติรวมกันได้
ชั้นนี้มีหน้าที่ "ตอบเมื่อมั่นใจเท่านั้น" ไม่ใช่ตัดสินทุกคำถาม — ไม่เจอคำในตารางให้ตกไปชั้น 2
ห้ามเดาว่าเป็น general_other เองตรงนี้ เพราะสองหมวดที่เหลือไม่มีคำดักเฉพาะ

**แก้ตารางนี้ทีไร ต้องรัน tests/eval_routing.py ใหม่ทุกครั้ง** เพิ่ม keyword ทีละคำแล้วดูว่า
accuracy ขึ้นหรือลง — keyword ที่มากเกินไปทำให้คำถามทั่วไป misroute โดยไม่มี error ให้เห็น
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from pythainlp.tokenize import word_tokenize

# ลำดับของหมวดในนี้คือลำดับในตาราง ใช้ตัดสินตอนจำนวนคำตรงเท่ากัน (กติกาข้อ 1)
KEYWORDS: dict[str, tuple[str, ...]] = {
    "connectivity": (
        "ไวไฟ", "วายฟาย", "wifi", "wi-fi", "เน็ต", "อินเทอร์เน็ต", "สัญญาณ",
        "เราเตอร์", "router", "ต่อเน็ต", "hotspot", "บลูทูธ", "bluetooth",
    ),
    "account_security": (
        "รหัสผ่าน", "พาสเวิร์ด", "password", "บัญชี", "account", "ล็อกอิน", "login",
        "โดนแฮก", "แฮก", "hack", "มิจฉาชีพ", "สแกม", "scam", "ลิงก์ปลอม", "ฟิชชิ่ง",
        "otp", "โอทีพี", "ยืนยันตัวตน",
    ),
    "device_performance": (
        "เครื่องช้า", "ช้ามาก", "อืด", "ค้าง", "หน่วง", "แบต", "แบตเตอรี่", "battery",
        "ชาร์จ", "ร้อน", "พื้นที่เต็ม", "เมมเต็ม", "storage", "ram", "ซีพียู",
    ),
    "data_backup": (
        "สำรองข้อมูล", "backup", "แบ็กอัพ", "ไฟล์หาย", "ข้อมูลหาย", "กู้ไฟล์", "กู้ข้อมูล",
        "cloud", "ไดรฟ์", "google drive", "icloud", "onedrive",
    ),
    "apps_updates": (
        "แอป", "app", "แอปพลิเคชัน", "อัปเดต", "update", "ลงโปรแกรม", "ติดตั้ง", "install",
        "เวอร์ชัน", "version", "play store", "app store", "ถอนการติดตั้ง",
    ),
    "hardware_media": (
        "จอ", "หน้าจอ", "screen", "กล้อง", "camera", "ไมค์", "ไมโครโฟน", "mic",
        "ลำโพง", "เสียง", "หูฟัง", "คีย์บอร์ด", "เมาส์", "พอร์ต", "สาย usb",
    ),
}

# กติกาข้อ 2: คำสั้นที่ชนคำทั่วไป ห้ามดักเดี่ยว ๆ ต้องมีคำอื่นในหมวดเดียวกันประกอบ
#   พอร์ต — "พอร์ตเกม", ram — ไปโผล่ในบริบทสเปกเครื่องทั่วไป
#   ร้อน — "อากาศร้อน" ไม่ใช่ปัญหาอุปกรณ์ แต่ "เครื่องร้อนตอนชาร์จ" ใช่
NEEDS_COMPANION = {"พอร์ต", "ram", "ร้อน"}

# แถวสุดท้ายของตาราง — ต้องมีทั้งคำสั่งและสิ่งที่ให้จำแนก ไม่ใช่เจอคำว่า "ประเภท" ลอย ๆ แล้วไป local_ai
LOCAL_VERBS = ("จำแนก", "จัดประเภท", "จัดหมวด", "หมวดหมู่", "classify", "categorize")
LOCAL_OBJECTS = ("คำร้อง", "คำถาม", "ข้อความ", "เคส", "request", "ticket")

# คำสั้นภาษาไทยที่ยาวไม่ถึงเกณฑ์ปลอดภัย จะถูกเช็กว่าตรงกับ "ขอบเขตคำ" ที่ pythainlp ตัดให้หรือไม่
# ตัวอย่างที่กันได้จริง: "เน็ต" ใน "อินเทอร์เน็ต" (ไม่เป็นไรเพราะหมวดเดียวกัน) และ "จอ" ใน "จอง" (คนละเรื่องเลย)
THAI_MIN_SAFE_LEN = 5

_ASCII_ONLY = re.compile(r"^[a-z0-9\s\-]+$")
_SPACES = re.compile(r"\s+")


@dataclass
class RuleMatch:
    route: str
    confidence: float
    reasoning: str
    category: str | None = None
    hits: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class Haystack:
    """ข้อความเดียวกันในสามรูปแบบ เตรียมครั้งเดียวแล้วใช้ซ้ำกับทุก keyword"""
    spaced: str        # ตัวพิมพ์เล็ก ช่องว่างเหลือช่องเดียว — ใช้กับคำอังกฤษ
    packed: str        # ตัดช่องว่างออกหมด — ใช้กับคำไทยที่ไม่มีเว้นวรรคอยู่แล้ว
    boundaries: set[int]   # ตำแหน่งขอบเขตคำใน packed ตามที่ pythainlp ตัดให้


def tokenize(text: str) -> list[str]:
    """ตัดคำด้วย pythainlp แล้วทิ้ง token ที่เป็นช่องว่าง"""
    return [t for t in word_tokenize(text.lower(), engine="newmm") if t.strip()]


def prepare(text: str) -> Haystack:
    spaced = _SPACES.sub(" ", text.lower()).strip()
    tokens = tokenize(spaced)
    packed, boundaries, pos = "", {0}, 0
    for tok in tokens:
        packed += tok
        pos += len(tok)
        boundaries.add(pos)
    return Haystack(spaced=spaced, packed=packed, boundaries=boundaries)


@lru_cache(maxsize=512)
def _ascii_pattern(word: str) -> re.Pattern[str]:
    # ขอบเขตคำแบบอังกฤษ กัน "app" ไปตรงกับ "apple" และ "ram" ไปตรงกับ "program"
    return re.compile(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])")


def contains(hay: Haystack, phrase: str) -> bool:
    word = phrase.lower().strip()
    if _ASCII_ONLY.match(word):
        return bool(_ascii_pattern(word).search(hay.spaced))

    needle = word.replace(" ", "")
    if needle not in hay.packed:
        return False
    if len(needle) >= THAI_MIN_SAFE_LEN:
        # ยาวพอจนโอกาสไปฝังกลางคำอื่นแบบบังเอิญต่ำมาก และ pythainlp ก็ตัดคำยาวไม่เหมือนกัน
        # ในแต่ละประโยค (เช่น "จำแนกประเภท" ติดกันเป็นคำเดียว) ถ้าบังคับขอบเขตจะพลาดของจริงแทน
        return True

    # คำสั้น: ต้องเริ่มและจบตรงขอบเขตคำที่ตัดได้ ไม่ใช่ฝังอยู่กลางคำอื่น
    start = hay.packed.find(needle)
    while start != -1:
        if start in hay.boundaries and (start + len(needle)) in hay.boundaries:
            return True
        start = hay.packed.find(needle, start + 1)
    return False


def _find_hits(hay: Haystack) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for category, words in KEYWORDS.items():
        found = [w for w in words if contains(hay, w)]
        # กติกาข้อ 2: เจอแต่คำที่ห้ามดักเดี่ยว ๆ ถือว่าหมวดนี้ไม่ตรง
        if found and all(w in NEEDS_COMPANION for w in found):
            continue
        if found:
            hits[category] = found
    return hits


def _is_local_ai(hay: Haystack) -> bool:
    return (any(contains(hay, v) for v in LOCAL_VERBS)
            and any(contains(hay, o) for o in LOCAL_OBJECTS))


def match(text: str) -> RuleMatch | None:
    """คืน RuleMatch เมื่อชั้นนี้มั่นใจ, None เมื่อไม่เจอคำในตาราง (ให้ตกไปชั้น 2)"""
    hay = prepare(text)

    if _is_local_ai(hay):
        return RuleMatch(route="local_ai", confidence=0.9,
                         reasoning="ชั้น rules: ผู้ใช้สั่งให้จำแนก/จัดประเภทข้อความโดยตรง")

    hits = _find_hits(hay)
    if not hits:
        return None

    # กติกาข้อ 1: หมวดที่มีจำนวนคำตรงมากที่สุดชนะ เท่ากันให้หมวดที่อยู่สูงกว่าในตารางชนะ
    order = list(KEYWORDS)
    best = max(hits, key=lambda c: (len(hits[c]), -order.index(c)))

    reason = f"ชั้น rules: เจอคำของหมวด {best} — {', '.join(hits[best])}"
    others = [f"{c} ({', '.join(words)})" for c, words in hits.items() if c != best]
    if others:
        # บันทึกหมวดที่ตรงด้วยทั้งหมด เวลา misroute จะได้ไล่ได้ว่าแพ้กันตรงไหน
        reason += f" · หมวดอื่นที่ตรงด้วย: {'; '.join(others)}"

    return RuleMatch(route="university_rag", confidence=0.9, reasoning=reason,
                     category=best, hits=hits)
