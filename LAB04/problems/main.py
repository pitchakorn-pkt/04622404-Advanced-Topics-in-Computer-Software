# -*- coding: utf-8 -*-
# Menu for the nine RAG problems found in this system.
#
# Run:
#     python main.py          menu
#     python main.py 4        one problem
#     python main.py 0        all of them
#
# Every problem reads the artefacts this repository already commits. Nothing
# downloads a model and nothing needs an API key, so a fresh clone can reproduce
# all nine in about ten seconds.

import sys

import data_loader   # noqa: F401  -- ต้อง import ก่อน เพื่อให้ปุ่ม path ของ LAB04 ติด

from problem01_hallucination import run as problem01
from problem02_vocabulary import run as problem02
from problem03_data_quality import run as problem03
from problem04_chunking import run as problem04
from problem05_metadata import run as problem05
from problem06_reranking import run as problem06
from problem07_generation import run as problem07
from problem08_config import run as problem08
from problem09_evaluation import run as problem09

PROBLEMS = {
    1: ("ตอบทั้งที่คลังไม่มีข้อมูล (Hallucination)", problem01),
    2: ("คำที่ผู้ใช้พิมพ์ไม่ตรงกับคำในคลัง (Vocabulary)", problem02),
    3: ("คุณภาพของคลังข้อมูล (Data Quality)", problem03),
    4: ("ขั้นแบ่ง chunk ไม่เคยทำงาน (Chunking)", problem04),
    5: ("metadata ที่เก็บไว้แต่ไม่มีใครใช้ (Metadata)", problem05),
    6: ("ค้นเจอแต่เรียงไม่เป็น (Re-ranking)", problem06),
    7: ("ค้นถูกแล้วแต่คำตอบเพี้ยน (Faithfulness)", problem07),
    8: ("ค่าตั้งที่เปลี่ยนตัวตนของระบบ (Configuration)", problem08),
    9: ("ตัววัดผลที่โกหกได้ (Evaluation)", problem09),
}


def show_menu():
    print()
    print("*" * 68)
    print("     LAB04 — ปัญหาของระบบ RAG ที่พัฒนาขึ้น และการแก้ไข")
    print("*" * 68)
    print(" 0. รันทั้งหมด")
    for number, (name, _) in PROBLEMS.items():
        print(f"{number:2}. {name}")
    print("*" * 68)


def execute(number):
    if number == 0:
        for no, (name, func) in PROBLEMS.items():
            print()
            print("=" * 68)
            print(f"ปัญหาข้อ {no}: {name}")
            print("=" * 68)
            func()
        return

    if number not in PROBLEMS:
        print("เลือกหมายเลข 0-9")
        return

    name, func = PROBLEMS[number]
    print()
    print("=" * 68)
    print(f"ปัญหาข้อ {number}: {name}")
    print("=" * 68)
    func()


def main_loop():
    while True:
        show_menu()
        choice = input("เลือกปัญหาที่ต้องการดู [0-9] หรือ Q เพื่อออก: ").strip()

        if choice.upper() == "Q":
            break

        try:
            execute(int(choice))
        except ValueError:
            print("ใส่ตัวเลข 0-9 หรือ Q")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        argument = sys.argv[1].strip()
        if argument.upper() == "Q":
            sys.exit(0)
        try:
            execute(int(argument))
        except ValueError:
            print("ใส่ตัวเลข 0-9 หรือ Q")
    else:
        main_loop()
