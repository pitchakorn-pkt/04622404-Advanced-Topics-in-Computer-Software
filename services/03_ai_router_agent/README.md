# 03 AI Router / Agent

compose service: `router` · ฟัง `0.0.0.0:8000` ข้างใน container

## ตอนนี้เป็น stub

ตอบค่าปลอมที่หน้าตาถูกตาม `docs/CONTRACT.md` เพื่อให้คนอื่นเรียกได้ตั้งแต่วันแรก
หาคำว่า `STUB: replace` ในโค้ดแล้วแทนด้วยของจริง **ห้ามเปลี่ยนรูปแบบ request/response**

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
make logs s=router
make rebuild s=router
```

## ไฟล์ที่ห้ามแก้

`app/common.py` เป็นของกลาง (health / X-Request-ID / log JSON)
`Dockerfile` เป็นของหัวหน้า ต้องเพิ่ม system package ให้บอกก่อน

รายละเอียดงานอยู่ในไฟล์ที่ปักหมุดในห้อง Discord ของโมดูลนี้
