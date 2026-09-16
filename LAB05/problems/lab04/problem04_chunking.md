# Problem 04 — The chunking stage has never run

English · [ภาษาไทย](problem04_chunking.th.md) · reproduce: `python main.py 4`

## What happens

`config.py` sets `CHUNK_SIZE = 400` and `CHUNK_OVERLAP = 50`, and
`build_index.py:49` calls `build_chunks()` on every record. Measured on the
committed index, the splitter has never split anything:

| | |
|---|---|
| records in | 194 |
| chunks out | 194 |
| chunks with `part_idx > 0` | 0 |
| shortest chunk | 306 characters |
| longest chunk | 392 characters |
| headroom below `CHUNK_SIZE` | 8 characters |

`CHUNK_OVERLAP = 50` therefore has no effect on this system whatsoever, and the
tuning notes in `config.py:56-58` describe a stage that does not execute.

## Why

`split_text()` returns the whole string immediately when it is shorter than the
threshold (`text_splitter.py:19-20`). `build_chunks()` assembles one string per
Q&A pair — `"Question: … Answer: …"` (`text_splitter.py:41`) — and in this
corpus no pair reaches 400 characters.

This is not a bug. One Q&A pair is already a complete unit of meaning, and
splitting it would only damage it. The problem is that the configuration
advertises a behaviour the system does not have, and nothing reports the
discrepancy.

## Why it is a risk rather than a defect

The longest chunk is 392 characters, eight below the threshold. Adding a single
longer answer starts the splitter, silently, and it splits by counting
characters with no regard for sentence or word boundaries.

Running `split_text()` on a 438-character answer:

```
ชิ้นที่ 0  (400 ตัวอักษร)
  ...ยไม่มีใครสังเกต แล้วรีสตาร์ตเครื่องหนึ่งครั้งเ
ชิ้นที่ 1  (88 ตัวอักษร)
  ๆ โดยไม่มีใครสังเกต แล้วรีสตาร์ตเครื่องหนึ่งครั้งเพื่อให้...
```

The first piece ends mid-word and the second begins mid-word. Thai has no
spaces, so a character-count split lands inside a word far more often than it
would in English. Those fragments become noise in the embedding and are
unreadable when passed to the LLM as context.

## How to check

`python main.py 4` prints two lines that answer it:

- **chunks with `part_idx > 0`** — still 0 means the stage is inert
- **longest chunk** — approaching `CHUNK_SIZE` means it is about to start

Run it after any change to the corpus or to `CHUNK_SIZE`. `build_index.py` will
not report it: the line that printed the chunk count is commented out
(`build_index.py:51`).

## What to do

The option that matches this corpus is to not split at all, and remove the
settings that have no effect — a Q&A pair is already the right retrieval unit.

If the stage is kept against future growth, it should split on sentence
boundaries rather than character counts, and `build_index.py` should print how
many chunks were actually split on every run. As it stands there is no signal at
all about what this stage did.

This has not been changed, because every number reported for this lab was
measured against the current index, and altering chunking would invalidate all
of them.

## The same finding in LAB02

LAB02 shows this in a stronger form: 90 records, 90 chunks, longest 314
characters against the same `CHUNK_SIZE = 400`. The stage has never run there
either. Two labs, two corpora, the same inert stage — which suggests the default
of 400 characters was chosen for a document-shaped corpus, not for a Q&A one.
