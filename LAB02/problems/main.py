# -*- coding: utf-8 -*-
# Menu for the six problems found in this retrieval system.
#
# Run:
#     python main.py          menu
#     python main.py 3        one problem
#     python main.py 0        all six
#
# Problems 1 and 3-5 load the embedding model, because reproducing them means
# encoding a query the corpus has never seen. It is the same model main.py uses
# and it is loaded once and shared.

import sys

import data_loader   # noqa: F401  -- ต้อง import ก่อน เพื่อให้ปุ่ม path ของ LAB02 ติด

from problem01_chunking import run as problem01
from problem02_metadata import run as problem02
from problem03_granularity import run as problem03
from problem04_topk import run as problem04
from problem05_no_refusal import run as problem05
from problem06_evaluation import run as problem06

PROBLEMS = {
    1: ("ขั้นแบ่ง chunk ไม่ทำงาน และเกณฑ์ใหญ่กว่าที่โมเดลอ่านได้", problem01),
    2: ("ชื่อเมนูที่เก็บไว้แต่ไม่มีใครใช้", problem02),
    3: ("หนึ่งเวกเตอร์ต่อหนึ่งคู่ถาม-ตอบ", problem03),
    4: ("แสดงผลอันดับเดียว และไม่มีขั้นจัดอันดับใหม่", problem04),
    5: ("ไม่มีทางบอกว่าคลังไม่มีเรื่องนี้", problem05),
    6: ("ไม่มีอะไรวัดผลเลย", problem06),
}


def show_menu():
    print()
    print("*" * 68)
    print("     LAB02 — ปัญหาของระบบค้นคืนที่พัฒนาขึ้น และการแก้ไข")
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
        print("เลือกหมายเลข 0-6")
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
        choice = input("เลือกปัญหาที่ต้องการดู [0-6] หรือ Q เพื่อออก: ").strip()
        if choice.upper() == "Q":
            break
        try:
            execute(int(choice))
        except ValueError:
            print("ใส่ตัวเลข 0-6 หรือ Q")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        argument = sys.argv[1].strip()
        if argument.upper() == "Q":
            sys.exit(0)
        try:
            execute(int(argument))
        except ValueError:
            print("ใส่ตัวเลข 0-6 หรือ Q")
    else:
        main_loop()
