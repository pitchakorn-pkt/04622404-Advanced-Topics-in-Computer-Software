"""เทสต์สั้นๆ ยืนยันว่า label ใน data/intents.csv ตรงกับ CONTRACT.md §3 เป๊ะ
รันด้วย: pytest test_intents.py  (หรือ python -m pytest test_intents.py)
"""
import csv
from pathlib import Path

CONTRACT_LABELS = {
    "connectivity",
    "account_security",
    "device_performance",
    "data_backup",
    "apps_updates",
    "hardware_media",
    "general_other",
    "out_of_scope",
}

CSV_PATH = Path(__file__).parent / "intents.csv"


def _load_labels() -> set[str]:
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["label"] for row in reader}


def test_label_set_matches_contract():
    labels_in_csv = _load_labels()
    assert labels_in_csv == CONTRACT_LABELS, (
        f"label ใน intents.csv ไม่ตรงกับ CONTRACT §3\n"
        f"เกินมา: {labels_in_csv - CONTRACT_LABELS}\n"
        f"ขาดไป: {CONTRACT_LABELS - labels_in_csv}"
    )


def test_each_label_has_enough_examples():
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        counts: dict[str, int] = {}
        for row in reader:
            counts[row["label"]] = counts.get(row["label"], 0) + 1
    for label in CONTRACT_LABELS:
        assert counts.get(label, 0) >= 20, (
            f"หมวด '{label}' มีตัวอย่างแค่ {counts.get(label, 0)} ข้อ ต้องมีอย่างน้อย 20"
        )