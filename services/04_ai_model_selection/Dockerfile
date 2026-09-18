# ใช้ slim เพราะ image เล็กกว่าตัวเต็มหลายเท่า และเราไม่ต้องใช้ของที่ตัดออก
FROM python:3.11-slim

# PYTHONUNBUFFERED: ให้ log ออกทันที ไม่ค้างใน buffer — สำคัญตอนไล่บั๊กด้วย docker logs
# PYTHONDONTWRITEBYTECODE: ไม่ต้องเขียน .pyc ลง container ที่เดี๋ยวก็ทิ้ง
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1

WORKDIR /srv

# คัดลอก requirements ก่อนโค้ด เพื่อให้ docker ใช้ cache ชั้นนี้ซ้ำได้
# แก้โค้ดแล้ว build ใหม่จะไม่ต้องลง package ใหม่ทั้งหมด
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# รันด้วยผู้ใช้ธรรมดา ไม่ใช่ root — ถ้าโดนเจาะจะเสียหายน้อยกว่า
# /models เป็น volume hf_models ที่ใช้ร่วมกับ retrieval ถ้า engines ขึ้นก่อนแล้วไม่มีจุดนี้ใน image
# docker จะสร้าง volume เป็นของ root แล้ว retrieval เขียนแคชโมเดลไม่ได้
RUN useradd -m -u 10001 app && mkdir -p /models && chown -R app:app /srv /models
USER app

EXPOSE 8000
# ต้อง bind 0.0.0.0 ไม่ใช่ 127.0.0.1 ไม่งั้น container อื่นเรียกไม่ถึง
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
