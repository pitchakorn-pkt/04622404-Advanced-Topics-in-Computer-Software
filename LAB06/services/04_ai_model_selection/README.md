# 04 AI Engines

compose service: `engines` · ฟัง `0.0.0.0:8000` ข้างใน container

## ตอนนี้เป็น stub

ทุก endpoint ตอบค่าปลอมที่หน้าตาถูกตาม `docs/CONTRACT.md` เพื่อให้คนอื่นเรียกได้ตั้งแต่วันแรก
หาคำว่า `STUB: replace` ในโค้ดแล้วแทนด้วยของจริง **ห้ามเปลี่ยนรูปแบบ request/response**

## รันเดี่ยวบนเครื่องตัวเอง

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
curl localhost:8000/health
```

## รันในระบบรวม

```bash
make up                 # ทั้งระบบ
make logs s=engines   # ดู log เฉพาะตัวนี้
make rebuild s=engines
```
ตอน dev ตัวนี้เปิด port ไว้ debug ด้วย ดูเลขใน `docker-compose.override.yml`

## ไฟล์ที่ห้ามแก้

`app/common.py` เป็นของกลาง (health / X-Request-ID / log JSON) แก้ได้เฉพาะเมื่อจำเป็นจริง
`Dockerfile` เป็นของหัวหน้า ถ้าต้องเพิ่ม system package ให้บอกในช่องของตัวเอง

รายละเอียดงานทั้งหมดอยู่ในไฟล์ที่ปักหมุดในห้อง Discord ของโมดูลนี้
