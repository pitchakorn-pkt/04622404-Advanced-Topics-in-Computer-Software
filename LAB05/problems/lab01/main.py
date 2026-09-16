# -*- coding: utf-8 -*-
# Menu for the six problems found in this data pipeline.
#
# Run:
#     python main.py          menu
#     python main.py 3        one problem
#     python main.py 0        all six
#
# Only problem 3 loads a model; the rest read the committed stage outputs and
# re-run the real cleaning functions over them.

import sys

import data_loader   # noqa: F401  -- ต้อง import ก่อน เพื่อให้ปุ่ม path ของ Pipeline ติด

from problem01_boilerplate import run as problem01
from problem02_schemas import run as problem02
from problem03_truncation import run as problem03
from problem04_dimension import run as problem04
from problem05_http import run as problem05
from problem06_citations import run as problem06

PROBLEMS = {
    1: ("กฎตัด boilerplate กินคุณสมบัติที่ผู้สมัครต้องมี", problem01),
    2: ("สอง schema และฟิลด์ที่กฎทำให้ว่างเปล่า", problem02),
    3: ("งบโทเคนนับด้วยตัวนับคนละตัวกับที่ใช้จ่าย", problem03),
    4: ("เวกเตอร์ที่สร้างคนละแบบเทียบกันไม่ได้", problem04),
    5: ("การเรียกข้ามเครือข่ายที่ล้มเหลวโดยไม่บอกสาเหตุ", problem05),
    6: ("คำตอบที่อ้างอิงประกาศซึ่งไม่มีอยู่จริง", problem06),
}


def show_menu():
    print()
    print("*" * 68)
    print("     LAB01 — ปัญหาของ data pipeline ที่พัฒนาขึ้น และการแก้ไข")
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
