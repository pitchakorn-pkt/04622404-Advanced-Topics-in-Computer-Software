"""รันชุดวัดผลทั้งระบบผ่าน /api/chat แล้วเขียนรายงานออกมาสองไฟล์

    python3 scripts/eval_e2e.py            (หรือ make eval)

วัด route accuracy, % คำตอบสาย RAG ที่มีแหล่งอ้างอิงจริง (sources ไม่ว่าง) และ latency

Groq free tier ได้ 8,000 token/นาที คำถาม RAG ข้อละ ~3,000-6,000 token ถ้ายิงติดกันจะโดน 429
แล้ว router ถอยไป clarify ทำให้ตัวเลขผิด — ตั้ง EVAL_SLEEP เว้นระยะต่อข้อ (วินาที)
    EVAL_SLEEP=30 python3 scripts/eval_e2e.py

ห้าม hardcode ตัวเลขลงรายงานเด็ดขาด ทุกเลขต้องมาจากการรันจริง
"""
from __future__ import annotations

import json
import os
import pathlib
import statistics
import sys
import time
import urllib.request

API = "http://localhost:8000"
SLEEP = float(os.getenv("EVAL_SLEEP", "0"))
ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "eval" / "golden.jsonl"
if not GOLDEN.exists():
    GOLDEN = ROOT / "eval" / "golden.example.jsonl"


def post(path, body, cookie=None):
    req = urllib.request.Request(API + path, method="POST",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          **({"Cookie": cookie} if cookie else {})})
    res = urllib.request.urlopen(req, timeout=95)
    return res, json.loads(res.read())


def main() -> int:
    try:
        res, _ = post("/api/auth/login", {"username": "student", "password": "student"})
    except Exception as exc:
        print(f"เข้าสู่ระบบไม่ได้ — ระบบขึ้นครบหรือยัง (make up)  [{exc}]")
        return 1
    cookie = res.headers.get("set-cookie", "").split(";")[0]

    items = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows, lat = [], []
    for it in items:
        t0 = time.perf_counter()
        try:
            _, d = post("/api/chat", {"session_id": None, "message": it["question"], "file_ids": []}, cookie)
            got, sources = d.get("route", ""), d.get("sources") or []
        except Exception as exc:
            got, sources = f"error: {exc}", []
        ms = int((time.perf_counter() - t0) * 1000)
        lat.append(ms)
        rows.append({**it, "got_route": got, "ok": got == it["expected_route"],
                     "latency_ms": ms, "has_citation": bool(sources)})
        time.sleep(SLEEP)

    acc = sum(r["ok"] for r in rows) / len(rows) if rows else 0.0
    cited = sum(r["has_citation"] for r in rows if r["expected_route"] == "university_rag")
    rag_n = sum(1 for r in rows if r["expected_route"] == "university_rag") or 1
    p95 = sorted(lat)[int(len(lat) * 0.95) - 1] if lat else 0
    summary = {"ข้อทั้งหมด": len(rows), "route accuracy": f"{acc:.2%}",
               "คำตอบสาย RAG ที่มีอ้างอิง": f"{cited}/{rag_n}",
               "latency เฉลี่ย": f"{int(statistics.mean(lat))} ms" if lat else "-",
               "latency p95": f"{p95} ms"}

    out = ROOT / "eval"
    md = ["# ผลวัดระบบ ช่วยด้วย (ChuayDuay)", "",
          f"รันเมื่อ {time.strftime('%Y-%m-%d %H:%M')} · ชุดทดสอบ `{GOLDEN.name}`", "",
          "| ตัวชี้วัด | ค่า |", "|---|---|",
          *[f"| {k} | {v} |" for k, v in summary.items()], "",
          "| # | คำถาม | ควรได้ | ได้จริง | ผ่าน | ms |", "|---|---|---|---|---|---|",
          *[f"| {r['id']} | {r['question']} | `{r['expected_route']}` | `{r['got_route']}` |"
            f" {'ใช่' if r['ok'] else 'ไม่'} | {r['latency_ms']} |" for r in rows]]
    (out / "report.md").write_text("\n".join(md), encoding="utf-8")

    cells = "".join(
        f"<tr><td>{r['id']}</td><td>{r['question']}</td><td><code>{r['expected_route']}</code></td>"
        f"<td><code>{r['got_route']}</code></td>"
        f"<td class='{'ok' if r['ok'] else 'no'}'>{'ผ่าน' if r['ok'] else 'ตก'}</td>"
        f"<td>{r['latency_ms']}</td></tr>" for r in rows)
    stat = "".join(f"<div class=card><b>{v}</b><span>{k}</span></div>" for k, v in summary.items())
    (out / "report.html").write_text(f"""<!doctype html><html lang=th><meta charset=utf-8>
<title>ผลวัดระบบ ช่วยด้วย</title><style>
body{{font-family:'Noto Sans Thai',system-ui,sans-serif;background:#0f1115;color:#e6e6e6;max-width:980px;margin:40px auto;padding:0 20px}}
h1{{font-size:26px}} .cards{{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}}
.card{{background:#161a22;border:1px solid #232834;border-radius:12px;padding:14px 18px;min-width:150px}}
.card b{{display:block;font-size:22px;color:#ff4d8d}} .card span{{font-size:13px;opacity:.65}}
table{{width:100%;border-collapse:collapse;font-size:14px}} th,td{{padding:8px 10px;border-bottom:1px solid #232834;text-align:left}}
th{{opacity:.6;font-weight:500}} code{{background:#1d222c;padding:1px 6px;border-radius:5px}}
.ok{{color:#4ade80}} .no{{color:#ff6b6b}} footer{{opacity:.45;font-size:13px;margin-top:28px}}
</style><h1>ผลวัดระบบ ช่วยด้วย (ChuayDuay)</h1>
<p style="opacity:.6">รันเมื่อ {time.strftime('%Y-%m-%d %H:%M')} · ชุดทดสอบ <code>{GOLDEN.name}</code></p>
<div class=cards>{stat}</div>
<table><tr><th>#</th><th>คำถาม</th><th>ควรได้</th><th>ได้จริง</th><th>ผล</th><th>ms</th></tr>{cells}</table>
<footer>ทุกตัวเลขมาจากการรันจริงผ่าน /api/chat ไม่มีค่าที่พิมพ์เอง</footer></html>""", encoding="utf-8")

    for k, v in summary.items():
        print(f"  {k:<28} {v}")
    print(f"\n  เขียนรายงานแล้ว: eval/report.md และ eval/report.html")
    return 0 if acc >= 0.8 else 1


if __name__ == "__main__":
    sys.exit(main())
