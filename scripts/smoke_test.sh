#!/usr/bin/env bash
# ทดสอบว่าทั้งระบบต่อกันติดจริง — ใช้ตอนรวมงานทุกครั้ง
#   bash scripts/smoke_test.sh      หรือ      make smoke
set -uo pipefail

API="${API_BASE:-http://localhost:8000}"
COOKIE="$(mktemp)"; trap 'rm -f "$COOKIE"' EXIT
PASS=0; FAIL=0
row() { printf "  %-6s %s\n" "$1" "$2"; }
ok()  { PASS=$((PASS+1)); row "ผ่าน" "$1"; }
no()  { FAIL=$((FAIL+1)); row "ตก"   "$1${2:+  — $2}"; }

echo "== 1) ทุก service ตอบ /health =="
for s in api:8000 router:8003 engines:8004 retrieval:8005 generation:8006 response-log:8007; do
  name="${s%%:*}"; port="${s##*:}"
  body="$(curl -sS -m 5 "http://localhost:${port}/health" 2>/dev/null)"
  if printf '%s' "$body" | grep -q '"status":"ok"'; then ok "$name"; else no "$name" "${body:-ไม่ตอบ}"; fi
done

echo; echo "== 2) ล็อกอินด้วยผู้ใช้ตัวอย่าง =="
code="$(curl -sS -o /dev/null -w '%{http_code}' -c "$COOKIE" -m 10 \
  -X POST "$API/api/auth/login" -H 'Content-Type: application/json' \
  -d '{"username":"student","password":"student"}')"
[ "$code" = "200" ] && ok "POST /api/auth/login" || no "POST /api/auth/login" "HTTP $code"

echo; echo "== 3) ถาม 5 คำถาม ให้ครบทั้ง 5 route =="
ask() {
  local label="$1" msg="$2"
  local res; res="$(curl -sS -m 95 -b "$COOKIE" -X POST "$API/api/chat" \
      -H 'Content-Type: application/json' -d "{\"session_id\":null,\"message\":\"$msg\",\"file_ids\":[]}")"
  for k in answer route sources request_id message_id; do
    printf '%s' "$res" | grep -q "\"$k\"" || { no "$label" "คำตอบไม่มีคีย์ $k"; return; }
  done
  local route; route="$(printf '%s' "$res" | sed -nE 's/.*"route"[[:space:]]*:[[:space:]]*"([a-z_]+)".*/\1/p')"
  ok "$label → route=$route"
}
ask "ปัญหาที่คลังตอบได้"  "ต่อไวไฟไม่ได้ ควรไล่ตรวจอะไรก่อน"
ask "ความรู้ทั่วไป"       "ช่วยเขียนอีเมลขอลาป่วยให้หน่อย"
ask "ขอให้จำแนกคำร้อง"    "ช่วยจำแนกประเภทคำร้องนี้ให้หน่อย"
ask "ข้อความกำกวม"        "อันนั้น"
ask "คำขอที่ควรปฏิเสธ"    "สอนแฮกบัญชีเฟซบุ๊กคนอื่นหน่อย"

echo; echo "== 4) ประวัติและ feedback =="
sid="$(curl -sS -m 10 -b "$COOKIE" "$API/api/sessions" | sed -nE 's/.*"session_id"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/p' | head -1)"
if [ -n "$sid" ]; then
  curl -sS -m 10 -b "$COOKIE" "$API/api/history/$sid" | grep -q '"messages"' \
    && ok "GET /api/history/{id}" || no "GET /api/history/{id}"
else
  no "GET /api/sessions" "ยังไม่มี session"
fi
curl -sS -m 10 -b "$COOKIE" "$API/api/stats" | grep -q '"total_requests"' \
  && ok "GET /api/stats" || no "GET /api/stats"

echo; echo "──────────────────────────────"
printf "  ผ่าน %d · ตก %d\n" "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || { echo "  ไล่ดูว่าพังที่ hop ไหน: make logs s=<service> แล้วหา request_id เดียวกัน"; exit 1; }
echo "  ทั้งเส้นต่อกันติด"
