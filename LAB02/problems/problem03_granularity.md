# Problem 03 — One vector per Q&A pair decides what can be answered

English · [ภาษาไทย](problem03_granularity.th.md) · reproduce: `python main.py 3`

## What happens

`build_chunks()` makes one chunk, and therefore one vector, out of each Q&A
pair. Retrieval is nearest-neighbour search over those 90 vectors. Running the
ten questions in `data/sample_questions.txt` through the real retriever splits
cleanly into two groups.

**Questions about one dish — 6 of the 10.** The corpus has a dedicated pair for
each:

| | question | top-1 |
|---|---|---|
| ✓ | ต้มยำกุ้งใส่อะไรบ้าง | ต้มยำกุ้งใส่อะไรบ้าง วัตถุดิบหลักมีอะไร · 0.8279 |
| ✓ | แกงเขียวหวานกับแกงมัสมั่นต่างกันยังไง | same question · 0.7289 |
| ✓ | ข้าวเหนียวมะม่วงทำยังไง | ข้าวเหนียวมะม่วงทำยังไง วิธีทำโดยย่อ · 0.7533 |
| ~ | ข้าวซอยเป็นอาหารภาคไหน | ข้าวซอย**ใส่อะไรบ้าง** · 0.7448 — right menu, wrong entry (correct one at rank 2, 0.7113) |
| ✓ | ผัดไทยกับผัดกะเพราใช้เส้นเหมือนกันไหม | same question · 0.6855 |
| ✓ | ลาบหมูปรุงรสด้วยอะไร | ลาบหมูปรุงรสด้วยอะไร · 0.7826 |

**Right menu: 6 of 6. Right entry: 5 of 6.** The one miss stays inside the
correct menu — see [problem 04](problem04_topk.md).

**Questions that span menus — 4 of the 10.** None is answered, and none can be:

| question | top-1 returned |
|---|---|
| เมนูไหนไม่เผ็ดบ้าง | [ผัดไทย] ผัดไทยเผ็ดไหม · 0.7312 |
| อาหารภาคอีสานมีเมนูอะไร | [ยำวุ้นเส้น] ยำวุ้นเส้นเป็นอาหารภาคไหน · 0.6859 |
| เมนูไหนเผ็ดที่สุด | [ผัดไทย] ผัดไทยเผ็ดไหม · 0.6594 |
| เมนูที่ใช้กะทิมีอะไรบ้าง | [ผัดไทย] ผัดไทยเผ็ดไหม · 0.5559 |

## Why

"เมนูไหนเผ็ดที่สุด" requires comparing spiciness across all 15 menus. The answer
is distributed over 15 pairs and lives in none of them. Nearest-neighbour search
has no vector to be near.

The system returns a pair that *talks about spiciness*, which genuinely is the
closest thing by meaning — but is not an answer to the question. This is not
mis-ranking. It is a question outside what the chosen structure can express, and
no amount of tuning reaches it.

## How to check

Split the test questions into two groups before measuring — those whose answer
lives in a single unit, and those that require aggregation — and report them
separately.

Combined, these ten produce "5 correct out of 10", which reads as a system that
retrieves about half the time. Separated, it is 6/6 on the menu and 5/6 on the
exact entry for one group, and 0/4 for a group that structurally cannot work.
Those are two different facts and one number hides both.

## What to do

This cannot be fixed by tuning; it needs a capability that is not there.

1. **Add summary-level pairs to the corpus** — "เมนูไหนใช้กะทิบ้าง" as its own
   Q&A entry. Most direct, and it fits the existing structure.
2. **Build a second index at menu level** and route by question type. Far more
   complex than this lab warrants.
3. **At minimum, tell the user what the system can answer.** Today it answers
   everything with the same confidence — see
   [problem 05](problem05_no_refusal.md).
