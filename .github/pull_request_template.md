<!-- ═══════════════════════════════════════════════════════════════
     ⚠️  เช็กก่อนอย่างอื่น: ช่องบนสุดของหน้านี้ต้องเป็น

            base: develop   ←   compare: feature/xx-ของคุณ

     ปุ่ม "Compare & pull request" จะเด้ง base เป็น main ให้เสมอ
     ถ้าเป็น main อยู่ ให้กด dropdown เปลี่ยนเป็น develop ก่อน
     (main รับ merge จาก develop เท่านั้น และต้อง approve 2 คน)
     ═══════════════════════════════════════════════════════════════ -->

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
