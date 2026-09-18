"""เทสต์ endpoint /local/classify ใน app/main.py — ครอบ 3 เรื่อง:
1. classify ได้ label ถูกต้องสำหรับ input ที่ชัดเจน (รวม edge case ที่เคยกำกวม
   ระหว่าง device_performance/hardware_media/connectivity ตอนเทรนโมเดล)
2. รูปแบบ response (data.label / data.score / data.top_k) ตรงตาม schema
3. กรณีไม่มีไฟล์โมเดล ต้องตอบ 503 MODEL_NOT_LOADED ไม่ใช่ 500 เฉยๆ

รันด้วย: pytest test_classify.py  (รันจาก services/04_ai_model_selection/)
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app

# หมายเหตุ: TestClient(app) จะ trigger startup event ของ main.py ด้วย รวมถึง
# check_primary_model ที่ยิงไปหา Groq จริง (ไม่มี API key ในเครื่องเทส) —
# ตัว main.py ครอบ try/except ไว้แล้วแค่ log warning ไม่ทำให้ startup ล้ม
# ใช้ scope="module" กันไม่ให้ยิงซ้ำทุกเทส
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# --- 1) ผลทำนายถูกต้องสำหรับ input ที่ชัดเจน ---
# เลือกประโยคที่ระหว่างเทรนโมเดล (train.py) เคยเป็นจุดกำกวมทับกันระหว่างหมวด
# ตัวอย่างนี้ทำหน้าที่เป็น regression guard: ถ้าใครมาแก้ data/intents.csv หรือ
# train.py แล้วทำให้ผลทำนายพวกนี้เพี้ยนไป จะรู้ทันที
EXPECTED_LABEL_CASES = [
    # เคยเป็น device_performance ผิด ก่อนย้ายไป hardware_media (เสียงพัดลม = ฮาร์ดแวร์)
    ("พัดลมระบายความร้อนในโน้ตบุ๊กดังผิดปกติ เกิดจากอะไร", "hardware_media"),
    # เคยเป็น general_other ผิด ก่อนย้ายไป connectivity (เชื่อมต่อไม่ได้ = ปัญหาเครือข่าย)
    ("เครื่องพิมพ์ไร้สายเชื่อมต่อไม่ได้ ควรตรวจอะไร", "connectivity"),
    # ตัวอย่างชัดเจนของแต่ละหมวดที่มักโดนทายผิดเข้ากันตอนเทรน
    ("หน้าจอมือถือแตกแต่ยังใช้ได้ ควรรีบเปลี่ยนไหม", "hardware_media"),
    ("มือถือช้าลงมาก ควรทำอะไรก่อน", "device_performance"),
    ("ไวไฟขึ้นว่าต่อแล้วแต่เข้าเน็ตไม่ได้ เพราะอะไร", "connectivity"),
    ("ลืมรหัสสำรองข้อมูลไอคลาวด์ ทำยังไงดี", "data_backup"),
]


@pytest.mark.parametrize("text, expected_label", EXPECTED_LABEL_CASES)
def test_classify_returns_expected_label(client, text, expected_label):
    resp = client.post("/local/classify", json={"request_id": "test-1", "text": text})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["label"] == expected_label, (
        f"input: {text!r} -> ได้ {body['data']['label']!r} "
        f"(คาดว่าจะได้ {expected_label!r})"
    )


# --- 2) รูปแบบ response ตรงตาม schema (EngineResult) ---
def test_classify_response_shape(client):
    resp = client.post(
        "/local/classify",
        json={"request_id": "test-2", "text": "ไวไฟบ้านช้า ควรไล่ตรวจอะไรก่อน"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["engine"] == "local_ai"
    assert isinstance(body["content"], str) and body["content"]

    data = body["data"]
    assert "label" in data and "score" in data and "top_k" in data
    assert isinstance(data["label"], str)
    assert 0.0 <= data["score"] <= 1.0

    top_k = data["top_k"]
    assert isinstance(top_k, list) and len(top_k) >= 1
    # top_k ต้องเรียงจากมั่นใจมากไปน้อย และ label แรกต้องตรงกับ data["label"]
    scores = [pair[1] for pair in top_k]
    assert scores == sorted(scores, reverse=True)
    assert top_k[0][0] == data["label"]


# --- 3) ไม่มีไฟล์โมเดล -> ต้องได้ 503 MODEL_NOT_LOADED ไม่ใช่ 500 ---
def test_classify_returns_503_when_model_missing(client, monkeypatch, tmp_path):
    # เก็บ cache เดิมไว้ก่อน แล้วบังคับให้ path ชี้ไปไฟล์ที่ไม่มีจริง + เคลียร์ cache
    original_bundle = main_module._local_model_bundle
    monkeypatch.setattr(main_module, "LOCAL_MODEL_PATH", tmp_path / "no_such_model.joblib")
    monkeypatch.setattr(main_module, "_local_model_bundle", None)

    resp = client.post(
        "/local/classify",
        json={"request_id": "test-3", "text": "ทดสอบตอนไม่มีโมเดล"},
    )

    assert resp.status_code == 503
    error = resp.json()["detail"]["error"]
    assert error["code"] == "MODEL_NOT_LOADED"

    # คืน cache เดิมกลับ กัน test อื่นที่รันหลังจากนี้ (ถ้ามี) โหลดโมเดลใหม่ไม่ทัน
    monkeypatch.setattr(main_module, "_local_model_bundle", original_bundle)
