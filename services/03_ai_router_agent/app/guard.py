"""ชั้น 0 ของ cascade — ด่านแรกก่อนใช้ตาราง rule base

หน้าที่มีสองอย่างเท่านั้น
  * ข้อความที่ตีความไม่ได้ (ว่าง สั้นเกิน ไม่มีเนื้อความ อ้างอิงลอย ๆ โดยไม่มีบทสนทนาก่อนหน้า) -> clarify
  * คำขอที่ไม่ควรตอบ -> decline

จุดที่พลาดง่ายที่สุดของชั้นนี้คือการแยก "ผู้ใช้โดนกระทำ" ออกจาก "ผู้ใช้อยากไปกระทำคนอื่น"
คำว่า "แฮก" อยู่ในตาราง rule base หมวด account_security ด้วย — "บัญชีโดนแฮก" ต้องได้คำตอบ
ไม่ใช่โดนปฏิเสธ ส่วน "สอนแฮกบัญชีคนอื่น" ต้องโดนปฏิเสธ ทั้งที่มีคำเดียวกัน
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .rules import contains, prepare

MIN_CHARS = 3

# มีคำพวกนี้ถือว่าอันตรายทันที ไม่ต้องดูบริบท (เขียนเป็นวลีไม่ใช่คำเดี่ยว
# เพราะ "ระเบิด" เฉย ๆ อาจมาจาก "แบตระเบิด" ซึ่งเป็นคำถามเรื่องอุปกรณ์จริง ๆ)
ALWAYS_DECLINE = (
    "ทำระเบิด", "ประกอบระเบิด", "วางระเบิด", "ยาเสพติด", "ยาบ้า", "ปืนเถื่อน",
    "ฆ่าคน", "วางยา", "ฟอกเงิน",
)

# การกระทำที่ "ผิดก็ต่อเมื่อผู้ใช้เป็นคนทำ" — ต้องดูบริบทประกอบเสมอ
HARM_ACTS = (
    "แฮก", "hack", "เจาะระบบ", "เจาะบัญชี", "ดักฟัง", "ดักข้อมูล", "สปายแวร์", "spyware",
    "แอบดู", "แอบอ่าน", "ขโมยรหัส", "ขโมยบัญชี", "ขโมยข้อมูล", "ปลอมบัตร", "บัตรปลอม",
    "ปลอมลายเซ็น", "โกงเงิน", "ดูดเงิน", "หลอกโอนเงิน", "หลอกเอาเงิน", "crack", "keygen",
    "โปรแกรมเถื่อน", "โหลดเถื่อน", "ของเถื่อน", "ปลดล็อกเครื่องคนอื่น",
    "สแปม", "spam", "ยิงข้อความ", "ปั่นยอด",
)

# เอกสาร/บัตรปลอม เขียนได้หลายแบบเกินกว่าจะไล่เป็นคำ ๆ ("บัตรนักศึกษาปลอม", "ปลอมสลิปโอนเงิน")
# ใช้รูปแบบแทน แล้วให้ผ่านเกณฑ์ actor/victim เดียวกับ HARM_ACTS
FORGERY_RE = re.compile(
    r"(บัตร|เอกสาร|ใบรับรอง|ใบปริญญา|ลายเซ็น|สลิป|ใบเสร็จ)[ก-ฮะ-ๅ]{0,12}ปลอม"
    r"|ปลอม[ก-ฮะ-ๅ]{0,12}(บัตร|เอกสาร|ใบรับรอง|ลายเซ็น|สลิป|ใบเสร็จ)")

# ผู้ใช้เป็นฝ่ายลงมือ
ACTOR_CUES = ("สอน", "วิธี", "ช่วยทำ", "ช่วยหา", "อยาก", "ขอวิธี", "ทำยังไงถึง",
              "เขียนโปรแกรม", "แนะนำวิธี", "how to", "ขอโปรแกรม", "ขอตัว")
# เป้าหมายเป็นคนอื่น — ตัวบ่งชี้ที่ชัดที่สุดว่าไม่ใช่การแก้ปัญหาของตัวเอง
TARGET_CUES = ("คนอื่น", "ผู้อื่น", "เพื่อน", "แฟน", "เพื่อนบ้าน", "ของเขา", "คนที่บ้าน",
               "หัวหน้า", "อาจารย์", "เหยื่อ")
# ผู้ใช้เป็นฝ่ายโดน หรือกำลังหาทางป้องกัน — พวกนี้คือคำถามที่เราต้องตอบ ไม่ใช่ปฏิเสธ
VICTIM_CUES = ("โดน", "ถูกแฮก", "ถูกขโมย", "ป้องกัน", "กันไม่ให้", "ระวัง", "เสี่ยง",
               "กู้คืน", "แก้ยังไง", "ตรวจสอบ", "สงสัยว่า", "เช็กว่า", "ปลอดภัย")

# คำอ้างอิงกลับที่ไม่มีความหมายในตัวเอง ถ้าไม่มีบทสนทนาก่อนหน้าก็ตีความไม่ได้
VAGUE_REFERENCES = ("อันนั้น", "อันนี้", "อันไหน", "อันเดิม", "แบบนั้น", "แบบนี้", "ตามนั้น",
                    "เมื่อกี้", "ตะกี้", "ที่บอกมา", "ที่บอกไป", "ข้างบน", "ยังไงต่อ", "แล้วล่ะ")

_MEANINGFUL = re.compile(r"[ก-ฮa-zA-Z0-9]")


@dataclass
class GuardResult:
    route: str
    confidence: float
    reasoning: str


def is_follow_up(query: str) -> bool:
    """ข้อความนี้อ้างถึงบทสนทนาก่อนหน้าหรือไม่ — ใช้ตัดสินว่าต้อง rewrite ก่อนค้นไหม"""
    hay = prepare(query)
    if any(contains(hay, w) for w in VAGUE_REFERENCES):
        return True
    # รูปแบบ "แล้ว...ล่ะ" เช่น "แล้วของปี 2 ล่ะ" — ประโยคเดียวที่พึ่งบริบทเต็ม ๆ
    return bool(re.search(r"แล้ว.{0,20}(ล่ะ|ล่ะครับ|ล่ะคะ)", query))


def _is_unsafe(query: str) -> tuple[bool, str]:
    hay = prepare(query)

    for phrase in ALWAYS_DECLINE:
        if contains(hay, phrase):
            return True, f"เข้าข่ายคำขอที่ผิดกฎหมาย (พบคำว่า '{phrase}')"

    acts = [w for w in HARM_ACTS if contains(hay, w)]
    forged = FORGERY_RE.search(query.replace(" ", ""))
    if forged:
        acts = acts + [forged.group(0)]
    if not acts:
        return False, ""

    # ผู้ใช้โดนกระทำหรือกำลังหาทางป้องกัน = คำถามปกติที่ต้องช่วย ไม่ใช่คำขอที่ต้องปฏิเสธ
    if any(contains(hay, w) for w in VICTIM_CUES):
        return False, ""

    actor = [w for w in ACTOR_CUES if contains(hay, w)]
    target = [w for w in TARGET_CUES if contains(hay, w)]
    if actor or target:
        cue = (actor + target)[0]
        return True, f"ผู้ใช้ขอวิธีทำสิ่งที่ไม่ควรทำ (พบ '{acts[0]}' คู่กับ '{cue}')"

    return False, ""


def check(query: str, history_len: int = 0) -> GuardResult | None:
    """คืน GuardResult เมื่อจบที่ชั้นนี้, None เมื่อให้ไปต่อชั้น 1"""
    text = (query or "").strip()

    if not text:
        return GuardResult("clarify", 0.9, "ชั้น guard: ข้อความว่าง")

    if len(text) < MIN_CHARS or len(_MEANINGFUL.findall(text)) < 2:
        return GuardResult("clarify", 0.9, "ชั้น guard: ข้อความสั้นเกินกว่าจะตีความได้")

    unsafe, why = _is_unsafe(text)
    if unsafe:
        return GuardResult("decline", 0.9, f"ชั้น guard: {why}")

    # อ้างอิงกลับลอย ๆ โดยไม่มีบทสนทนาก่อนหน้า -> ถามกลับ
    # ถ้ามี history ไม่ต้องถาม เพราะเราจะ rewrite คำถามจากบริบทให้เองที่ชั้นถัดไป
    if history_len == 0 and is_follow_up(text) and len(text) <= 25:
        return GuardResult("clarify", 0.9,
                           "ชั้น guard: ข้อความอ้างอิงถึงเรื่องก่อนหน้าแต่ยังไม่มีบทสนทนา")

    return None
