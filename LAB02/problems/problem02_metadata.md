# Problem 02 — The menu name is stored and never used

English · [ภาษาไทย](problem02_metadata.th.md) · reproduce: `python main.py 2`

## What happens

The corpus is 15 menus with 6 Q&A pairs each, and the menu name is the category
on every chunk. Scanning the four files on the retrieval path
(`retriever.py`, `embedding_model.py`, `vector_store.py`, `main.py`):

| | |
|---|---|
| live lines referencing `category` | 0 |
| commented-out lines | 1 — `main.py:30` |

```python
#print(f"Category: {item['category']}")
```

That commented line comes from the lab template and was not changed here. The
code in `src/` and `labs/` is the template unchanged; the contribution in this
lab is the 90-pair Thai food dataset. These are problems in the system as it
stands, not a list of mistakes made along the way.

The user therefore sees only the answer text — no menu, no matched question, no
way to tell whether the right entry was found.

## What it costs

The six questions repeat across all 15 menus — *ใส่อะไรบ้าง*, *เป็นอาหารภาคไหน*,
*เผ็ดไหม*, *ทำยังไง*, and so on. Sentence structure is therefore identical
across menus, and the only thing distinguishing them is a short menu name.

For **47 of the 90 chunks**, the nearest neighbour in the whole corpus belongs
to a different menu, at very high similarity:

| cosine | | |
|---|---|---|
| 0.9354 | [แกงเขียวหวานไก่] แกงเขียวหวานไก่มีรสชาติเด่นอย่างไร | [ต้มข่าไก่] ต้มข่าไก่มีรสชาติเด่นอย่างไร |
| 0.9347 | [ต้มยำกุ้ง] ต้มยำกุ้งมีรสชาติเด่นอย่างไร | [แกงส้มชะอมกุ้ง] แกงส้มชะอมกุ้งมีรสชาติเด่นอย่างไร |
| 0.9340 | [ลาบหมู] ลาบหมูมีรสชาติเด่นอย่างไร | [หมูปิ้ง] หมูปิ้งมีรสชาติเด่นอย่างไร |

This is the corpus where filtering by category would help most, and it is the
corpus that does not use it at all.

## Is the menu name in the embedded text?

83 of 90 chunks contain their own category string — but only because the
questions naturally name the dish. The other 7 use a shortened form
(`แกงเขียวหวาน` where the category is `แกงเขียวหวานไก่`).

Both cases say the same thing: the menu name is in the index as a side effect of
how the questions were written, not because the system puts it there. It cannot
be relied on.

## What to do

1. **Uncomment the display lines in `main.py`.** One-line change, no rebuild,
   and it lets the user verify the answer themselves.
2. **Add the menu name to the embedded text.** Requires a rebuild and
   re-measurement.
3. **Filter by menu when the question names one.** The menus here are cleanly
   separated, so a wrong guess is far less likely than in LAB04's overlapping
   corpus.
