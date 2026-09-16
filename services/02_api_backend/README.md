# 02 API / Backend

compose service: `api` · ฟัง `0.0.0.0:8000` · **เปิดออกเครื่องจริงที่ port 8000**

## ตอนนี้เป็น stub

auth ใช้ผู้ใช้ตัวอย่างในหน่วยความจำ ยังไม่ต่อ postgres — แต่ `/api/chat` **เรียก router และ response-log จริง**
ผู้ใช้ตัวอย่าง: `student/student` · `staff/staff` · `demo/demo`

```bash
curl -c /tmp/c -X POST localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"student","password":"student"}'
curl -b /tmp/c -X POST localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"session_id":null,"message":"ต่อไวไฟไม่ได้","file_ids":[]}'
```

หาคำว่า `STUB: replace` แล้วแทนด้วยของจริง **ห้ามเปลี่ยนรูปแบบ request/response**

## ลำดับ 10 ขั้นของ /api/chat

ใส่หมายเลขกำกับไว้ในโค้ดแล้ว ทำผิดลำดับจะพังเงียบ ที่สำคัญที่สุดคือ
**ตอบ ChatResponse (ขั้น 9) ต้องมาก่อนยิง log (ขั้น 10) เสมอ** ไม่งั้นผู้ใช้รอนานขึ้นฟรี ๆ

## ไฟล์ที่ห้ามแก้

`app/common.py` ของกลาง · `Dockerfile` ของหัวหน้า

รายละเอียดงานอยู่ในไฟล์ที่ปักหมุดในห้อง Discord ของโมดูลนี้
