## ทำอะไรไป


## ทดสอบยังไง


## มี dependency ใหม่ไหม
<!-- ถ้ามี เขียนชื่อไว้ด้วย หัวหน้าอาจต้องแก้ Dockerfile (เช่น libmagic, tesseract, poppler) -->


---

## เช็กก่อนขอ review

- [ ] `git diff --stat origin/develop` แก้เฉพาะโฟลเดอร์ของตัวเอง
- [ ] ไม่มี `.env`, API key, ไฟล์โมเดล, index หรือไฟล์เกิน 5 MB
- [ ] service รันได้ และ `GET /health` ตอบ
- [ ] ตอบ JSON ตรงตาม `docs/CONTRACT.md` (ถ้าต้องแก้ contract ให้แยกเป็นอีก PR)
- [ ] อัปเดต `requirements.txt` / `package.json` แล้วถ้าเพิ่ม dependency
- [ ] อัปเดต README ในโฟลเดอร์ตัวเองถ้าวิธีรันเปลี่ยน
- [ ] commit message เป็นรูปแบบ `type(nn-module): ทำอะไร`
