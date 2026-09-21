# 01 Web App

compose service: `web` · ฟัง `3000` · **เปิดออกเครื่องจริงที่ http://localhost:3000**

## ตอนนี้เป็น stub

หน้า login + หน้า chat ที่ต่อ `api` ได้จริงแล้ว แสดง badge route กับ sources ได้แล้ว
ยังไม่มี: ประวัติ sidebar, ปุ่ม 👍👎, แผง trace, อัปโหลดไฟล์, dashboard

ผู้ใช้ตัวอย่าง `student` / `student`

## รันเดี่ยว

```bash
npm install
API_URL=http://localhost:8000 npm run dev     # ต้องมี api รันอยู่ที่ 8000
```

## สองเรื่องที่พลาดบ่อย

**อย่าเอา URL ภายใน docker ไปใส่ `NEXT_PUBLIC_*`** ค่าพวกนั้นถูกฝังลงไฟล์ตอน build
และหลุดถึงเบราว์เซอร์ซึ่งไม่รู้จักชื่อ `api` — ให้ผ่าน rewrites ฝั่ง server ใน `next.config.mjs` เท่านั้น

**ห้ามโชว์ค่า route ดิบ** เช่น `university_rag` ให้ผู้ใช้เห็น แปลงเป็นป้ายภาษาคนก่อน
ตาราง `ROUTE_LABEL` ใน `app/page.tsx` ทำไว้ให้แล้ว

รายละเอียดงานทั้งหมดอยู่ในไฟล์ที่ปักหมุดในห้อง `#01-web`
