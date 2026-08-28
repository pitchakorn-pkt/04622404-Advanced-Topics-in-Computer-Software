# data_loader.py
# Shared loader for the problem scripts in this folder.
#
# Reads the Pipeline stage outputs that this repository commits — the raw
# Collection output, the cleaned records, the chunks, and the boilerplate set —
# and re-runs the real cleaning functions over them. Only the truncation problem
# loads an embedding model.

import glob
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE = os.path.join(BASE_DIR, "Pipeline")
OUTPUTS = os.path.join(PIPELINE, "outputs")
sys.path.insert(0, PIPELINE)        # ให้ import cleaning / chunking / embedding ได้

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8")


def _load_group(prefix):
    """คืน dict {ชื่อแหล่ง: [record, ...]} จากไฟล์ที่ขึ้นต้นด้วย prefix"""
    group = {}
    for path in sorted(glob.glob(os.path.join(OUTPUTS, f"{prefix}*.json"))):
        name = os.path.basename(path)[len(prefix):-len(".json")]
        with open(path, "r", encoding="utf-8") as f:
            group[name] = json.load(f)
    if not group:
        raise SystemExit(f"ไม่พบไฟล์ {prefix}*.json ใน {OUTPUTS}")
    return group


def raw_records():
    """ผลจากขั้น Collection ก่อนทำความสะอาด"""
    return _load_group("extracted_text_")


def cleaned_records():
    """ผลหลังขั้น Cleaning + Normalization"""
    return _load_group("cleaned_")


def chunks():
    """chunk ทั้งหมดจากขั้น Chunking รวมทุกแหล่ง"""
    return [c for records in _load_group("chunked_").values() for c in records]


def boilerplate_lines():
    """บรรทัดที่ขั้นทำความสะอาดตัดสินว่าเป็น boilerplate — บันทึกไว้ตอนรันจริง"""
    with open(os.path.join(OUTPUTS, "boilerplate_lines.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def flat_raw():
    """record ดิบทุกอันรวมกัน ไม่แยกแหล่ง"""
    return [r for records in raw_records().values() for r in records]


def jobicy_only(records):
    """เฉพาะ record จาก Jobicy ซึ่งเป็นแหล่งเดียวที่บอกชื่อบริษัท"""
    return [r for r in records if isinstance(r.get("companyName"), str)]


def head(text, n=70):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def rule(title=""):
    print("-" * 72)
    if title:
        print(title)
        print("-" * 72)
