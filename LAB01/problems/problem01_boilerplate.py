# -*- coding: utf-8 -*-
# Problem 01: the boilerplate rule removes real requirements from some employers
#
# collect_boilerplate() drops any line appearing in five or more documents, on
# the reasoning that a line repeated across unrelated postings is a company
# blurb rather than part of the job. That holds only if the postings are
# independent of each other. In this corpus they are not: one employer accounts
# for 36 of the 160 Jobicy postings, and its postings repeat each other by
# nature.

from collections import defaultdict

from data_loader import boilerplate_lines, flat_raw, head, jobicy_only, rule

from cleaning import KEEP_BOILERPLATE_FIELDS, TEXT_FIELDS, clean, collect_boilerplate

# บรรทัดที่ถูกตัดทิ้งทั้งที่เป็นคุณสมบัติที่ผู้สมัครต้องมี ไม่ใช่คำโฆษณาบริษัท
REQUIREMENTS_REMOVED = [
    "Experience with Linux (Debian or Ubuntu preferred)",
    "Experience with Microsoft Office Suite (Word, Excel, PowerPoint)",
    "Bachelor's Degree in Computer Science or related field preferred",
]


def rebuild_boilerplate(records):
    """สร้างชุด boilerplate ใหม่ด้วยกฎเดียวกับที่ขั้นทำความสะอาดใช้จริง"""
    texts = [
        record[field]
        for record in records
        for field in TEXT_FIELDS
        if field not in KEEP_BOILERPLATE_FIELDS and isinstance(record.get(field), str)
    ]
    return collect_boilerplate(texts)


def run():
    records = flat_raw()
    rebuilt = rebuild_boilerplate(records)
    committed = set(boilerplate_lines())

    rule("ทำซ้ำชุด boilerplate จากไฟล์ที่ commit ไว้")
    print(f"  คำนวณใหม่จาก record {len(records)} อัน : {len(rebuilt)} บรรทัด")
    print(f"  ไฟล์ boilerplate_lines.json     : {len(committed)} บรรทัด")
    print(f"  ตรงกันทุกบรรทัด                  : {set(rebuilt) == committed}")
    print()

    rule("กฎที่ใช้")
    print("  ตัดบรรทัดที่ปรากฏใน 'เอกสารตั้งแต่ 5 ฉบับขึ้นไป' (นับเอกสาร ไม่ใช่นับครั้ง)")
    print("  ยกเว้นบรรทัดที่ยาวไม่เกิน 4 คำ ซึ่งถือว่าเป็นหัวข้อ และขั้น chunking ใช้")
    print("  มันเป็นขอบเขตของหัวข้อ (cleaning.py:73-91)")
    print()
    print("  เหตุผลของกฎ: บรรทัดที่ซ้ำกันข้ามประกาศที่ไม่เกี่ยวกันคือคำโฆษณาบริษัท")
    print("  ซึ่งจริงก็ต่อเมื่อประกาศแต่ละฉบับเป็นอิสระต่อกัน")
    print()

    jobicy = jobicy_only(records)
    counts = defaultdict(int)
    for record in jobicy:
        counts[record["companyName"]] += 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:4]

    rule("แต่ประกาศในคลังนี้ไม่ได้เป็นอิสระต่อกัน")
    print(f"  ประกาศจาก Jobicy ทั้งหมด {len(jobicy)} ฉบับ จากนายจ้าง {len(counts)} ราย")
    for employer, n in top:
        print(f"    {employer:<26} {n:>3} ฉบับ")
    print(f"    นายจ้างที่มีประกาศเดียว      {sum(1 for n in counts.values() if n == 1):>3} ราย")
    print()
    print("  นายจ้างรายเดียวลงประกาศ 36 ฉบับ ประกาศของเขาย่อมซ้ำกันเองโดยธรรมชาติ")
    print("  บรรทัดของเขาจึงข้ามเกณฑ์ 5 เอกสารได้โดยที่ไม่ใช่คำโฆษณาเลยสักนิด")
    print()

    rule("ผลกระทบ แยกตามนายจ้าง — เฉพาะส่วนที่กฎ boilerplate ทำ")
    stats = defaultdict(lambda: [0, 0, 0])
    for record in jobicy:
        employer = record["companyName"]
        text = record["jobDescription"]
        stats[employer][0] += 1
        stats[employer][1] += len(clean(text))                # ไม่ตัด boilerplate
        stats[employer][2] += len(clean(text, rebuilt))       # ตัด boilerplate
    rows = sorted(stats.items(), key=lambda kv: -kv[1][0])

    print(f"  {'employer':<26}{'ฉบับ':>6}{'ข้อความที่เหลือ':>16}")
    for employer, (n, without, with_bp) in rows[:5]:
        print(f"  {employer:<26}{n:>6}{with_bp/without*100:>15.0f}%")
    singles = [v for v in stats.values() if v[0] == 1]
    share = sum(v[2] for v in singles) / sum(v[1] for v in singles) * 100
    print(f"  {'นายจ้างที่มีประกาศเดียว':<26}{len(singles):>6}{share:>15.0f}%")
    print()
    print("  นายจ้างที่ลงประกาศเดียวไม่เสียข้อความให้กฎนี้เลยแม้แต่ตัวอักษรเดียว")
    print("  ส่วน iHerb ที่ลง 5 ฉบับเหลือข้อความ 41% — กฎนี้ลงโทษตามจำนวนประกาศ")
    print("  ที่นายจ้างลง ไม่ได้ลงโทษตามว่าข้อความนั้นเป็นคำโฆษณาจริงหรือไม่")
    print()

    rule("บรรทัดที่ถูกตัดทั้งที่ไม่ใช่คำโฆษณา")
    for line in REQUIREMENTS_REMOVED:
        mark = "อยู่ในชุดที่ตัด" if line in committed else "ไม่พบในชุด"
        print(f"  [{mark}] {head(line, 58)}")
    print()
    print("  ทั้งสามบรรทัดคือคุณสมบัติที่ผู้สมัครต้องมี ถูกลบออกจากทุกประกาศที่ระบุไว้")
    print("  ผลตรงถึงคำถามตัวอย่างใน README — การค้นว่าใครรับสมัครงาน Kubernetes")
    print("  จะได้คำตอบจากประกาศที่ข้อความระบุว่าต้องใช้ Linux หายไปแล้ว")
    print()

    rule("วิธีตรวจสอบ")
    print("  1. รันสคริปต์นี้แล้วดูคอลัมน์ 'ข้อความที่เหลือ' ถ้ากระจายกว้างมากระหว่าง")
    print("     นายจ้าง แปลว่ากฎกำลังลงโทษตามจำนวนประกาศ ไม่ใช่ตามเนื้อหา")
    print()
    print("  2. อ่าน outputs/boilerplate_lines.json ด้วยตาทั้ง 77 บรรทัด")
    print("     ไฟล์นี้ถูกบันทึกไว้ทุกครั้งที่รันขั้นทำความสะอาดก็เพื่อการนี้")
    print()

    rule("แนวทางแก้ที่ยังไม่ได้ทำ")
    print("  นับ 'จำนวนนายจ้างที่บรรทัดนั้นปรากฏ' แทน 'จำนวนเอกสาร'")
    print("  คำโฆษณาที่บริษัทหลายรายใช้เหมือนกันจะยังถูกตัด ส่วนคุณสมบัติที่บริษัท")
    print("  เดียวเขียนซ้ำในประกาศของตัวเองจะรอด")
    print()
    print("  ยังไม่เปลี่ยน เพราะผลลัพธ์ที่ commit ไว้คือสิ่งที่ขั้นถัดไปทั้งหมด")
    print("  ถูกสร้างและวัดผลบนมัน การเปลี่ยนกฎแปลว่าต้องรันใหม่ทั้งสาย")


if __name__ == "__main__":
    run()
