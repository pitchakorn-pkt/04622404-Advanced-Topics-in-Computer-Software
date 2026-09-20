# 02 API / Backend

compose service: `api` · ฟัง `0.0.0.0:8000` · **เปิดออกเครื่องจริงที่ port 8000**

## auth

ใช้ตาราง `users` ใน postgres (เก็บรหัสผ่านเป็น bcrypt hash)
api สร้างตารางและเพิ่มผู้ใช้ตัวอย่างให้เองตอนเริ่มทำงาน ไม่ต้องรันอะไรเพิ่ม

ผู้ใช้ตัวอย่าง: `student/student` · `staff/staff` · `demo/demo`

token เก็บใน cookie ชื่อ `access_token` (`HttpOnly`, `SameSite=lax`, `Path=/`)

## ลองใช้

```bash
curl -c /tmp/c -X POST localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"student","password":"student"}'
curl -b /tmp/c -X POST localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"session_id":null,"message":"ต่อไวไฟไม่ได้","file_ids":[]}'
```

หรือเปิด `http://localhost:8000/docs` แล้วกด Try it out ได้ทุก endpoint (cookie ติดให้เอง)
Windows ใช้ `curl.exe` ไม่ใช่ `curl`

## ทดสอบ

```bash
docker compose exec api python -m pytest -q
```

ชุดทดสอบจำลอง router และ 07 ด้วย `httpx.MockTransport` และไม่ต่อ postgres
จึงรันได้โดยไม่ต้องเปิด service อื่นและไม่กินโควตา Groq
แต่ด้วยเหตุนี้จึงไม่ยืนยันว่าเข้ากับของจริงได้ ก่อนสาธิตยังต้องยิงผ่าน `/docs` กับของจริง

## ลำดับ 10 ขั้นของ /api/chat

ใส่หมายเลขกำกับไว้ในโค้ดแล้ว ทำผิดลำดับจะพังเงียบ ที่สำคัญที่สุดคือ
**ตอบ ChatResponse (ขั้น 9) ต้องมาก่อนยิง log (ขั้น 10) เสมอ** ไม่งั้นผู้ใช้รอนานขึ้นฟรี ๆ

## ยังไม่ได้ทำ

- `/api/upload` ยังเป็น stub ตอบ 501 (ตาราง `uploaded_files` สร้างไว้แล้ว)
- ตัวนับ rate limit เก็บในหน่วยความจำ จึงเริ่มนับใหม่ทุกครั้งที่ api รีสตาร์ต

## ไฟล์ที่ห้ามแก้

`app/common.py` ของกลาง · `Dockerfile` ของหัวหน้า

รายละเอียดงานอยู่ในไฟล์ที่ปักหมุดในห้อง Discord ของโมดูลนี้