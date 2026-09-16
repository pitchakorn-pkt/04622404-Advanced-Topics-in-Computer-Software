# -*- coding: utf-8 -*-
# เมนูรวมของปัญหาทั้ง 21 ข้อจาก LAB01, LAB02 และ LAB04
#
# Run:
#     python main.py            เมนู
#     python main.py lab02      รันทั้งชุดของ LAB02
#     python main.py lab04 6    รันข้อ 6 ของ LAB04
#     python main.py 0          รันทั้งหมด (ทั้งสามชุด)
#
# ตัวรันนี้เรียก main.py ของแต่ละชุดในโฟลเดอร์ของมันเอง ด้วย interpreter ตัว
# เดียวกับที่เรียกไฟล์นี้ สคริปต์ยังอ่านข้อมูลจาก LAB01/ LAB02/ LAB04/ ตามเดิม

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SETS = {
    "lab01": ("LAB01", 6, "data pipeline ของงานทีม — ทำความสะอาด, chunk, embed, อ้างอิง"),
    "lab02": ("LAB02", 6, "RAG คลังคำถามอาหารไทย — chunk, metadata, top-k, การวัดผล"),
    "lab04": ("LAB04", 9, "RAG ปัญหามือถือ/คอมพิวเตอร์ — hallucination, คำศัพท์, rerank, การวัดผล"),
}


def run_set(key, number=None):
    folder = os.path.join(HERE, key)
    argv = [sys.executable, "main.py"]
    argv.append(str(number) if number is not None else "0")
    # flush ก่อนเรียก subprocess ไม่งั้นหัวข้อจะไปโผล่ท้ายไฟล์ตอน redirect ออกไฟล์
    print()
    print("#" * 72)
    print(f"#  {SETS[key][0]} — {SETS[key][2]}")
    print("#" * 72, flush=True)
    return subprocess.call(argv, cwd=folder)


def show_menu():
    print()
    print("*" * 72)
    print("     LAB05 — ปัญหาของทุกระบบที่พัฒนาขึ้นในวิชานี้ รวม 21 ข้อ")
    print("*" * 72)
    print(" 0. รันทั้งหมด")
    for key, (lab, count, desc) in SETS.items():
        print(f" {key}. {lab} — {count} ข้อ: {desc}")
    print(" q. ออก")
    print()


def main():
    args = [a.lower() for a in sys.argv[1:]]

    if args and args[0] in SETS:
        number = args[1] if len(args) > 1 else None
        sys.exit(run_set(args[0], number))

    if args and args[0] == "0":
        for key in SETS:
            run_set(key)
        return

    if args:
        print(f"ไม่รู้จักตัวเลือก {args[0]!r} — ใช้ lab01 / lab02 / lab04 / 0")
        sys.exit(2)

    while True:
        show_menu()
        choice = input("เลือก: ").strip().lower()
        if choice in ("q", "quit", "exit", ""):
            return
        if choice == "0":
            for key in SETS:
                run_set(key)
            return
        if choice in SETS:
            run_set(choice)
            return
        print(f"ไม่มีตัวเลือก {choice!r}")


if __name__ == "__main__":
    main()
