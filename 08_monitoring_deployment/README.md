# 08 Docker / Integration / Monitoring

โฟลเดอร์นี้กับไฟล์ที่ราก (`docker-compose*.yml`, `Makefile`, `.env.example`, `scripts/`, `eval/`)
เป็นของหัวหน้าทีม ตาม `.github/CODEOWNERS`

## คำสั่งที่ใช้บ่อย

```bash
make            # ดูคำสั่งทั้งหมด
make up         # ขึ้นทั้งระบบ รอจนทุกตัว healthy
make ps         # ตัวไหนยังไม่ healthy
make logs s=router
make smoke      # ทดสอบทั้งเส้น
make eval       # รันชุดวัดผล เขียน eval/report.md + report.html
```

## ลำดับคิดเวลารวมงานแล้วพัง

1. `make ps` — ตัวไหนไม่ healthy
2. `make logs s=<ตัวนั้น>` — หา `request_id` เดียวกันไล่ทีละ hop
3. พังที่ "กล่อง" (port, env, volume, network, Dockerfile) → **หัวหน้าแก้**
4. พังที่ "ของข้างใน" (logic, schema ไม่ตรง contract) → **เปิด Issue แท็กเจ้าของ ห้ามแก้เอง**
5. contract ไม่พอหรือผิด → คุยใน `#contract-changes` แล้วแก้ผ่าน PR แยก

## Prometheus + Grafana

ยังไม่ได้ทำ เป็นงาน Could ถ้าทำให้ใส่ไว้หลัง `profiles: ["monitoring"]`
ใน compose เพื่อไม่ให้มันขึ้นมาเองตอน `make up` ปกติ
