"""วัด route accuracy จาก tests/routing_cases.jsonl

    python tests/eval_routing.py                 # cascade เต็ม (ต้องมี engines + API key)
    python tests/eval_routing.py --offline       # เฉพาะชั้น 0-1 ไม่ยิง service ไหนเลย
    python tests/eval_routing.py --cases <path>

วัดเฉพาะ "การตัดสินใจ" ไม่ได้เรียก execution plan จริง — ตั้งใจให้เป็นแบบนั้น
เพราะการรันชุดนี้ทุกครั้งที่แก้ตาราง keyword ต้องเร็วและต้องไม่กินโควตา LLM ไปกับการสร้างคำตอบ

รันจากโฟลเดอร์ services/03_ai_router_agent — ถ้ารันบนเครื่องตัวเอง (ไม่ได้อยู่ใน docker)
ให้ชี้ ENGINES_URL ไปที่ port ที่เปิดไว้ debug เช่น ENGINES_URL=http://localhost:8004
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# รันบนเครื่องตัวเองจะเรียกชื่อ service ใน docker ไม่ได้ ใช้ port ที่ override เปิดไว้แทน
os.environ.setdefault("ENGINES_URL", "http://localhost:8004")

import httpx  # noqa: E402

from app import cascade, clients, llm  # noqa: E402
from app.budget import Budget, Steps  # noqa: E402

ROUTES = ("university_rag", "general_ai", "local_ai", "clarify", "decline")


def load_cases(path: Path) -> list[dict]:
    cases = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def go_offline() -> None:
    """ตัดชั้น 2 และ 3 ออก เพื่อดูว่าชั้น 0-1 เดี่ยว ๆ ครอบคลุมได้แค่ไหนและแม่นแค่ไหน"""
    async def _no_classifier(*_args, **_kwargs):
        raise clients.HopError("engines.classify", "ปิดไว้ในโหมด offline")

    async def _no_llm(*_args, **_kwargs):
        return None

    clients.classify = _no_classifier
    llm.decide_route = _no_llm


async def run(cases: list[dict], delay: float = 0.0) -> list[dict]:
    results = []
    async with httpx.AsyncClient() as client:
        for index, case in enumerate(cases):
            # free tier ของ Groq จำกัด token ต่อนาที ยิง 40 ข้อติดกันจะชน limit
            # แล้วผลที่ได้จะต่ำกว่าความจริง — เว้นจังหวะด้วย --delay ตอนวัดเลขจริง
            if delay and index:
                await asyncio.sleep(delay)
            budget, steps = Budget(), Steps()
            started = time.perf_counter()
            decision = await cascade.decide(case["query"], case.get("history", []),
                                            client, budget, steps, f"eval-{case['id']}")
            results.append({
                "id": case["id"],
                "query": case["query"],
                "expected": case["expected_route"],
                "expected_category": case.get("expected_category"),
                "got": decision.route,
                "category": decision.category,
                "layer": decision.layer,
                "confidence": round(decision.confidence, 2),
                "reasoning": decision.reasoning,
                "ms": int((time.perf_counter() - started) * 1000),
                "note": case.get("note", ""),
            })
    return results


def report(results: list[dict], offline: bool) -> float:
    total = len(results)
    hit = sum(1 for r in results if r["got"] == r["expected"])
    accuracy = hit / total if total else 0.0

    print("\n=== ข้อที่ยังไม่ตรง ===")
    misses = [r for r in results if r["got"] != r["expected"]]
    if not misses:
        print("ไม่มี")
    for r in misses:
        print(f"  [{r['id']}] {r['query'][:48]}")
        print(f"       คาดหวัง {r['expected']} · ได้ {r['got']} (ชั้น {r['layer']}) — {r['reasoning'][:90]}")

    print("\n=== แยกตาม route ===")
    print(f"  {'route':<16}{'ถูก/ทั้งหมด':>14}{'accuracy':>12}")
    for route in ROUTES:
        rows = [r for r in results if r["expected"] == route]
        if not rows:
            continue
        ok = sum(1 for r in rows if r["got"] == route)
        print(f"  {route:<16}{f'{ok}/{len(rows)}':>14}{ok / len(rows):>12.0%}")

    print("\n=== confusion matrix (แถว = ที่ควรเป็น, คอลัมน์ = ที่ได้จริง) ===")
    header = "".join(f"{r[:9]:>11}" for r in ROUTES)
    print(f"  {'':<16}{header}")
    for expected in ROUTES:
        rows = [r for r in results if r["expected"] == expected]
        if not rows:
            continue
        counts = Counter(r["got"] for r in rows)
        cells = "".join(f"{counts.get(got, 0):>11}" for got in ROUTES)
        print(f"  {expected:<16}{cells}")

    print("\n=== ชั้นที่ตัดสินใจ ===")
    layers = Counter(r["layer"] for r in results)
    no_llm = sum(v for k, v in layers.items() if k != "llm")
    for layer in ("guard", "rules", "classifier", "llm"):
        count = layers.get(layer, 0)
        if count:
            avg = sum(r["ms"] for r in results if r["layer"] == layer) / count
            print(f"  {layer:<12}{count:>4} ข้อ ({count / total:>4.0%})  เฉลี่ย {avg:>7.0f} ms")
    print(f"  ตัดสินใจได้โดยไม่เรียก LLM {no_llm}/{total} ({no_llm / total:.0%})")

    avg_ms = sum(r["ms"] for r in results) / total if total else 0
    print(f"\n=== สรุป ===")
    print(f"  route accuracy {hit}/{total} = {accuracy:.1%}" + ("  (โหมด offline: ชั้น 0-1 เท่านั้น)" if offline else ""))
    print(f"  เวลาตัดสินใจเฉลี่ย {avg_ms:.0f} ms")
    return accuracy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(Path(__file__).parent / "routing_cases.jsonl"))
    parser.add_argument("--offline", action="store_true",
                        help="ปิดชั้น 2 และ 3 — ใช้ดูว่าตาราง keyword เดี่ยว ๆ ทำได้แค่ไหน")
    parser.add_argument("--json", dest="json_out", help="เขียนผลดิบเป็นไฟล์ JSON")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="เว้นจังหวะระหว่างข้อ (วินาที) กันชน rate limit ของ Groq ตอนวัดเลขจริง")
    args = parser.parse_args()

    if args.offline:
        go_offline()

    cases = load_cases(Path(args.cases))
    results = asyncio.run(run(cases, delay=args.delay))
    accuracy = report(results, args.offline)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
        print(f"  เขียนผลดิบไว้ที่ {args.json_out}")

    # ไม่ได้ทำให้ CI แดงเอง — ตัวเลขคือของที่ต้องเอาไปบันทึกใน README
    return 0 if accuracy >= 0.85 else 1


if __name__ == "__main__":
    sys.exit(main())
