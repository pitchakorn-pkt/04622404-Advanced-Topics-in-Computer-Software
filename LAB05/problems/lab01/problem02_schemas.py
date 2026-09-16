# -*- coding: utf-8 -*-
# Problem 02: two schemas in one corpus, and a field the cleaning rule empties
#
# The Collection stage produces records from two sources with different field
# names and different id types. And one field, jobExcerpt, is the opening of
# jobDescription — so the corpus-wide boilerplate rule sees it as a repeat of
# text it has already decided to drop, and empties it.
#
# Both are reproduced here against the committed Collection output.

from data_loader import flat_raw, head, raw_records, rule

from cleaning import KEEP_BOILERPLATE_FIELDS, TEXT_FIELDS, clean, collect_boilerplate, normalize


def collect(records, include_excerpt):
    """เก็บ boilerplate โดยเลือกได้ว่าจะนับ jobExcerpt เป็นเอกสารด้วยหรือไม่"""
    texts = [
        record[field]
        for record in records
        for field in TEXT_FIELDS
        if isinstance(record.get(field), str)
        and (include_excerpt or field not in KEEP_BOILERPLATE_FIELDS)
    ]
    return collect_boilerplate(texts)


def run():
    sources = raw_records()
    records = flat_raw()

    rule("สอง schema ในคลังเดียวกัน")
    for name, group in sources.items():
        sample = group[0]
        text_fields = [f for f in TEXT_FIELDS if isinstance(sample.get(f), str)]
        print(f"  {name}")
        print(f"    record          {len(group)}")
        print(f"    ชนิดของ id       {type(sample['id']).__name__}  (เช่น {sample['id']!r})")
        print(f"    ฟิลด์ข้อความ      {text_fields}")
    print()
    print("  Jobicy ใช้ camelCase กับ id ที่เป็นจำนวนเต็ม ส่วน AIDevBoard ใช้ snake_case")
    print("  กับ id ที่เป็นสตริง UUID ทั้งสองใช้คีย์ชื่อ 'id' เหมือนกัน")
    print()
    print("  ถ้าเขียนโค้ดจากสเปกโดยไม่เปิดดูข้อมูลจริง จะเห็นแค่ schema เดียว")
    print("  แล้วอีกแหล่งจะผ่านขั้นทำความสะอาดไปทั้งอย่างนั้นโดยไม่มี error")
    print("  เพราะ process_records() แตะเฉพาะฟิลด์ที่มีอยู่จริง (cleaning.py:130-131)")
    print("  record ที่ไม่มีฟิลด์ตรงชื่อจะถูกคัดลอกไปเฉย ๆ ทั้งก้อน")
    print()

    rule("ฟิลด์ที่กฎ boilerplate จะทำให้ว่างเปล่า")
    excerpts = [r for r in records if isinstance(r.get("jobExcerpt"), str)]

    for include in (True, False):
        boilerplate = collect(records, include)
        emptied = sum(
            1 for r in excerpts if not normalize(clean(r["jobExcerpt"], boilerplate)).strip()
        )
        label = "นับ jobExcerpt เป็นเอกสารด้วย" if include else "ไม่นับ (ที่ใช้จริง)"
        print(f"  {label:<32} boilerplate {len(boilerplate):>3} บรรทัด  excerpt ที่ว่างเปล่า {emptied:>3}/{len(excerpts)}")
    print()
    print("  jobExcerpt คือย่อหน้าเปิดของ jobDescription ซึ่งมักเป็นคำโฆษณาบริษัท")
    print("  ถ้านับมันเป็นเอกสารอีกฉบับ ข้อความเดียวกันจะถูกนับสองครั้งต่อประกาศหนึ่งฉบับ")
    print("  ข้ามเกณฑ์ 5 เอกสารได้ง่ายขึ้น แล้วถูกตัดจนฟิลด์ว่าง 30 จาก 160 record")
    print()
    print("  แก้ด้วยสองอย่างที่ต้องทำคู่กัน")
    print("    1. ยกเว้น jobExcerpt จากการ 'ถูกตัด'      (KEEP_BOILERPLATE_FIELDS)")
    print("    2. ยกเว้นมันจากการ 'ถูกนับ' ด้วย           (02_data_cleaning.py:50-56)")
    print()
    print("  ถ้าทำแค่ข้อ 1 ฟิลด์จะไม่ว่าง แต่ข้อความในนั้นจะยังไปดันให้บรรทัดของ")
    print("  jobDescription ข้ามเกณฑ์เร็วกว่าที่ควร ตัวเลขสองแถวข้างบนคือส่วนต่างนั้น")
    print()

    rule("ตัวอย่าง excerpt ที่จะหายไปถ้าไม่ยกเว้น")
    boilerplate_with = collect(records, True)
    shown = 0
    for record in excerpts:
        if not normalize(clean(record["jobExcerpt"], boilerplate_with)).strip():
            print(f"  {record['companyName']}")
            print(f"    {head(record['jobExcerpt'], 62)}")
            shown += 1
            if shown == 3:
                break
    print()

    rule("กฎที่เหลือไว้อีกข้อ และเหตุผล")
    print("  บรรทัดที่ยาวไม่เกิน 4 คำจะไม่ถูกตัด แม้จะซ้ำเกินเกณฑ์ (cleaning.py:36)")
    print('  เพราะมันคือหัวข้ออย่าง "Requirements" หรือ "The Role" ซึ่งขั้น chunking')
    print("  ใช้เป็นขอบเขตในการแบ่ง — chunk ทุกชิ้นในคลังนี้ใช้ strategy 'heading'")
    print()
    print("  ตัดหัวข้อทิ้งเมื่อไหร่ ขั้นถัดไปจะแบ่ง chunk ไม่ถูกที่ทันที")
    print("  เป็นตัวอย่างว่าการตัดสินใจในขั้นหนึ่งผูกกับขั้นถัดไปแค่ไหน")


if __name__ == "__main__":
    run()
