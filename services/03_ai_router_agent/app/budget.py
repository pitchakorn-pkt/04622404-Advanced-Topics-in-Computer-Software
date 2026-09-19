"""งบเวลารวม 70 วินาทีของทั้ง request (CONTRACT ข้อ 0)

timeout ต่อ hop อย่างเดียวไม่พอ: rag เส้นยาวสุดคือ rewrite + search + generate
ถ้าแต่ละ hop ใช้เต็มเพดานของตัวเอง รวมกันจะเกิน 75s ที่ api รอไว้ แล้วผู้ใช้เห็น 504
ทั้งที่คำตอบกำลังจะเสร็จ — คลาสนี้จึงตัด timeout ของ hop ถัดไปตามเวลาที่เหลือจริง
"""
from __future__ import annotations

import time
from contextlib import contextmanager

from .config import MIN_HOP, RESERVE, TOTAL_BUDGET


class Budget:
    def __init__(self, total: float = TOTAL_BUDGET) -> None:
        self.total = total
        self._t0 = time.perf_counter()

    def elapsed(self) -> float:
        return time.perf_counter() - self._t0

    def elapsed_ms(self) -> int:
        return int(self.elapsed() * 1000)

    def remaining(self) -> float:
        return self.total - self.elapsed()

    def hop(self, cap: float) -> float | None:
        """timeout ที่ใช้ได้จริงสำหรับ hop ถัดไป — None แปลว่าเวลาไม่พอ ให้ข้าม hop นั้น"""
        allowed = min(cap, self.remaining() - RESERVE)
        return allowed if allowed >= MIN_HOP else None


class Steps:
    """เก็บเวลาที่ใช้ต่อ hop สำหรับ field `trace` (CONTRACT ข้อ Object ที่ใช้ร่วม)

    ข้อมูลนี้ไหลผ่านเราอยู่แล้ว ต้นทุนที่เพิ่มคือศูนย์ แต่เก็บย้อนหลังไม่ได้ถ้าไม่ใส่ตั้งแต่แรก
    หน้าเว็บเอาไปโชว์ว่า agent ตัดสินใจที่ชั้นไหนและเวลาหมดไปกับ hop ไหน
    """

    def __init__(self) -> None:
        self.items: list[dict] = []

    @contextmanager
    def step(self, name: str):
        started = time.perf_counter()
        try:
            yield
        finally:
            self.add(name, int((time.perf_counter() - started) * 1000))

    def add(self, name: str, ms: int) -> None:
        self.items.append({"name": name, "ms": ms})
