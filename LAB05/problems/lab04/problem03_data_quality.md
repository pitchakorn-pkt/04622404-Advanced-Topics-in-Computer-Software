# Problem 03 — What the corpus is made of decides what can be right

English · [ภาษาไทย](problem03_data_quality.th.md) · reproduce: `python main.py 3`

## What happens

The committed corpus passes every structural check:

| | |
|---|---|
| `Q:` lines in the file | 194 |
| `A:` lines in the file | 194 |
| records parsed | 194 |
| records with no category | 0 |
| exactly duplicated questions | 0 |
| chunk pairs above cosine 0.90 | 0 |

That is a clean result, and it says less than it appears to. It means this file
happens to be well formed — not that the loader would tell anyone if it were
not, and not that the content is true.

## The parser says nothing when the file is wrong

Feeding a deliberately malformed file through the real `load_qa_file()`:

```
[หมวด: หมวดที่หนึ่ง]
Q: คำถามที่มีคำตอบครบ
A: คำตอบที่หนึ่ง

Q: คำถามที่ไม่มีบรรทัด A ตามมา

Q: คำถามถัดไปหลังจากข้อที่หายไป
A: คำตอบที่สอง

หมวด: หมวดที่สอง (ลืมวงเล็บเหลี่ยม)
Q: คำถามที่ควรอยู่หมวดที่สอง
A: คำตอบที่สาม
```

Four `Q:` lines go in. Three records come out, all filed under the first
category, with no warning of any kind.

- The question with no answer is dropped. `document_loader.py:36` only commits a
  record when an `A:` line follows a `Q:`, and says nothing when one does not.
- The category heading that lost its brackets is not recognised.
  `document_loader.py:31` tests for a `[หมวด` prefix, so the malformed line is
  skipped as ordinary text and the last record inherits the previous category.

Neither is wrong as code. Both are silent, and `build_index.py` prints no
counts either — the lines that would have (`build_index.py:46,51`) are commented
out. So a corpus can lose entries between the file and the index with nothing on
screen to show for it.

## Near-duplicates are deliberate here

No pair reaches cosine 0.90. The closest sit between 0.83 and 0.87:

| cosine | | |
|---|---|---|
| 0.8633 | จะรู้ได้ยังไงว่าถึงเวลาต้องเปลี่ยนแบตแล้ว | ควรเปลี่ยนมือถือใหม่ตอนไหน |
| 0.8582 | ไวไฟบ้านช้า ควรไล่ตรวจอะไรก่อน | เน็ตมือถือช้ากับไวไฟช้า แยกยังไง |
| 0.8549 | เครื่องขึ้นว่าหน่วยความจำไม่พอทั้งที่พื้นที่ยังเหลือ | แรมเต็มกับพื้นที่เก็บข้อมูลเต็ม อาการต่างกันยังไง |

These were added on purpose. The corpus grew from 172 pairs to 194 by writing 22
entries designed to sit close to existing ones. The average scores barely moved
— misses went from 3 to 4 — but the number of questions that flip between
configurations widened and the significance improved by an order of magnitude.
A corpus where every entry is far from every other produces high, pretty scores
that cannot tell two configurations apart. See
[problem 09](problem09_evaluation.md).

## The failure that cost a rebuild

None of the above is why this lab changed domain. The first corpus was
IoT/embedded, and checking it against the real documentation found 5 of roughly
15 sampled facts wrong:

- ESP32 boots at 115200, not 74880 — that figure belongs to the ESP8266
- a per-pin current of 12 mA that is not the figure Espressif publishes
- board dimensions and a camera module that did not match the actual part

No retrieval metric can see this. `eval_retrieval` compares the chunk ids
returned against the chunk ids the golden set names. Retrieve the right chunk
and the score is full marks, whether the sentence inside it is true or false.
The system was free to retrieve correctly and answer wrongly, while every number
in the report said it was working.

The fix was to replace the corpus with everyday phone and computer problems,
where answers are procedural advice rather than specification numbers that have
to be checked one by one against a source.

**The lesson:** do not build a dataset full of specification figures unless
there is time to verify each one against real documentation. Prefer a domain
where the answers are methods.

## How to check

- count `Q:` and `A:` lines and compare against `len(records)` after every
  corpus edit — `python main.py 3` does this
- look at the closest pairs by cosine; above 0.90 means genuine duplicates to
  remove, 0.80–0.90 means deliberate distractors or a genuinely fine distinction
- for factual accuracy there is no automated check. It has to be read.
