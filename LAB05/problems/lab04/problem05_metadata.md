# Problem 05 — Every chunk carries a category and nothing reads it

English · [ภาษาไทย](problem05_metadata.th.md) · reproduce: `python main.py 5`

## What happens

`document_loader.py:32` parses the `[หมวด: …]` headings, `text_splitter.py:47`
copies the value onto every chunk, and all 194 chunks in
`vector_db/chunk_store.json` carry it:

| count | category |
|---|---|
| 27 | แบตเตอรี่และการชาร์จ |
| 24 | เครื่องช้าและพื้นที่เต็ม |
| 22 | อินเทอร์เน็ตและไวไฟ |
| 22 | มิจฉาชีพและความปลอดภัย |
| 20 | บัญชีและรหัสผ่าน |
| 17 | ข้อมูลและการสำรอง |
| 16 | แอปและการอัปเดต |
| 16 | การใช้งานเอกสารและงานทั่วไป |
| 15 | หน้าจอ เสียง และกล้อง |
| 15 | การเลือกซื้อและดูแลเครื่อง |

Scanning the ten files on the retrieval path — `query_transform.py`,
`hybrid_retriever.py`, `retriever.py`, `rerankers.py`, `vector_store.py`,
`generator.py`, `prompt_templates.py`, `rag_pipeline.py`, `serve.py`, `main.py`
— finds **zero** references to the field. The only code that reads it is
`evaluation/build_golden_set.py:141`, which uses it to spread the test questions
across categories. Nothing at query time.

It is not in the embedded text either. `text` is built from
`"Question: … Answer: …"` and nothing else, so 0 of 194 chunks contain their own
category name. The value is invisible to dense retrieval and to BM25 alike.

## What it costs

**Category-level questions cannot be answered.** "เรื่องมิจฉาชีพมีอะไรบ้าง" or
"สรุปหมวดแบตให้หน่อย" need a sweep of a category. The system only has
nearest-neighbour search for `k` chunks, so it returns the three closest and
lets the LLM write as though those were the whole picture.

**Nothing prevents cross-category confusion.** For 28 of the 194 chunks, the
single nearest neighbour in the corpus belongs to a different category:

| cosine | | |
|---|---|---|
| 0.8633 | แบตเตอรี่และการชาร์จ — จะรู้ได้ยังไงว่าถึงเวลาต้องเปลี่ยนแบตแล้ว | การเลือกซื้อและดูแลเครื่อง — ควรเปลี่ยนมือถือใหม่ตอนไหน |
| 0.8223 | เครื่องช้าและพื้นที่เต็ม — มือถือช้าลงมาก ควรทำอะไรก่อน | แอปและการอัปเดต — อัปเดตแล้วเครื่องช้าลง แก้ยังไง |
| 0.8111 | เครื่องช้าและพื้นที่เต็ม — ลบแอปกับถอนการติดตั้งต่างกันไหม | แอปและการอัปเดต — ปิดแอปกับปิดการทำงานเบื้องหลัง ต่างกันยังไง |

The reranking case in [problem 06](problem06_reranking.md) is exactly this: the
question "มือถือตกน้ำต้องทำอะไรก่อน" is ranked first by chunk 16
(เครื่องช้าและพื้นที่เต็ม) while the correct chunk 90 sits in
หน้าจอ เสียง และกล้อง at rank 5. A category filter would have made that
mis-ranking impossible.

## How to check

`python main.py 5` scans the retrieval path and prints the number of references
it finds. While it prints 0, the field is dead weight. By hand:

```
grep -rn category src/ serve.py main.py
```

and read whether the lines found *write* the field or *read* it. Here they all
write it.

## What could be done, and why neither was

**Filter before searching.** Guess the category from the question and search only
within it. This works well when categories are cleanly separated. This corpus
overlaps heavily — see the pairs above — and a wrong guess means finding nothing
at all rather than merely ranking badly. That is a worse failure than the one it
fixes.

**Put the category into the embedded text.** One line at `text_splitter.py:41`.
Cheaper, and it cannot cause a miss — it only adds signal. It requires a full
index rebuild and re-measurement of every table in the report, because every
vector changes.

The second is the better option and remains undone for that reason: all reported
numbers were measured on the current index.
