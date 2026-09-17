# 07 Response / Log

compose service: `response-log` · ฟัง `0.0.0.0:8000` ข้างใน container

## ตอนนี้เปลี่ยนเป็น Postgres แล้ว

โครงสร้าง Table: `conversations`, `messages`, `feedback`, `request_logs` (สำหรับเช็ก idempotent)
ทุก Endpoint ตอบค่าได้ตรงตาม `CONTRACT.md` เป๊ะ

## รันเดี่ยว

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
curl localhost:8000/health
```

## รันในระบบรวม

```bash
make up
make logs s=response-log
make rebuild s=response-log
```

## ตัวอย่าง cURL ทุก Endpoint

**1. POST /log (บันทึกแชท)**
```bash
curl -X POST http://localhost:8007/log \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-123",
    "session_id": "sess-456",
    "user_id": "user-789",
    "user_message_id": "msg-001",
    "assistant_message_id": "msg-002",
    "user_message": "ต่อไวไฟไม่ได้",
    "answer": "วิธีต่อไวไฟ...",
    "route": "university_rag",
    "trace": {"decided_at_layer": "rules"}
  }'
```

**2. GET /history/{session_id}**
```bash
curl "http://localhost:8007/history/sess-456?user_id=user-789&limit=20"
```

**3. GET /sessions**
```bash
curl "http://localhost:8007/sessions?user_id=user-789"
```

**4. POST /feedback**
```bash
curl -X POST http://localhost:8007/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "msg-002",
    "user_id": "user-789",
    "rating": 1
  }'
```

**5. GET /stats**
```bash
curl "http://localhost:8007/stats?days=7"
```

**6. GET /stats/routes (สัดส่วนว่า Router ตัดสินใจที่ Layer ไหน)**
```bash
curl "http://localhost:8007/stats/routes?days=7"
```

## ไฟล์ที่ห้ามแก้

`app/common.py` เป็นของกลาง (health / X-Request-ID / log JSON)
`Dockerfile` เป็นของหัวหน้า ต้องเพิ่ม system package ให้บอกก่อน
