# คำสั่งลัดของโปรเจกต์ — พิมพ์ `make` เฉย ๆ เพื่อดูรายการทั้งหมด
SHELL := /bin/bash
COMPOSE := docker compose

.DEFAULT_GOAL := help
.PHONY: help up down build rebuild logs ps smoke warmup ingest eval backup clean

help:  ## แสดงคำสั่งทั้งหมด
	@grep -hE '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n",$$1,$$2}'

up:  ## ขึ้นทั้งระบบแล้วรอจนทุกตัว healthy
	$(COMPOSE) up -d --wait
	@echo "พร้อมแล้ว → http://localhost:3000  (api: http://localhost:8000/health)"

down:  ## ปิดทั้งระบบ (ข้อมูลใน volume ยังอยู่)
	$(COMPOSE) down

build:  ## build ทุก image
	$(COMPOSE) build

rebuild:  ## build ใหม่เฉพาะตัวเดียว เช่น make rebuild s=router
	$(COMPOSE) build --no-cache $(s) && $(COMPOSE) up -d $(s)

logs:  ## ดู log เช่น make logs s=router (ไม่ใส่ s = ดูทุกตัว)
	$(COMPOSE) logs -f --tail=100 $(s)

ps:  ## ดูว่าตัวไหนขึ้นแล้ว healthy ไหม
	$(COMPOSE) ps

smoke:  ## ทดสอบว่าต่อกันติดทั้งเส้น
	@bash scripts/smoke_test.sh

warmup:  ## ดึงโมเดลลง volume ก่อนใช้งานจริง — ต้องทำครั้งแรกบนทุกเครื่อง
	@echo "ดึงโมเดล embedding ลง volume (ครั้งแรกใช้เวลาหลายนาที ~1 GB)"
	$(COMPOSE) run --rm retrieval python -c "import os; from huggingface_hub import snapshot_download; snapshot_download(os.environ['EMBEDDING_MODEL'])" \
		|| echo "ยังไม่มีโค้ดจริงของ 05 — ข้ามไปก่อนได้"

ingest:  ## สร้างดัชนีค้นหาจากเอกสารใน services/05_retrieval_knowledge/data
	$(COMPOSE) run --rm retrieval python ingest.py

eval:  ## รันชุดวัดผลทั้งระบบ แล้วเขียน eval/report.md + report.html
	python3 scripts/eval_e2e.py

backup:  ## สำรอง postgres ลงไฟล์ backup/
	@mkdir -p backup
	$(COMPOSE) exec -T postgres pg_dump -U $${POSTGRES_USER:-chuayduay} $${POSTGRES_DB:-chuayduay} \
		> backup/chuayduay-$$(date +%Y%m%d-%H%M).sql
	@echo "เก็บไว้ที่ backup/"

clean:  ## ลบ container และ volume ทั้งหมด (ข้อมูลหายถาวร)
	@read -p "ลบ volume ทั้งหมด ข้อมูลใน postgres และดัชนีจะหายถาวร พิมพ์ yes เพื่อยืนยัน: " ok; \
	if [ "$$ok" = "yes" ]; then $(COMPOSE) down -v; else echo "ยกเลิก"; fi
