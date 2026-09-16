# Problem 01 — Chunking never runs, and its setting exceeds the model

English · [ภาษาไทย](problem01_chunking.th.md) · reproduce: `python main.py 1`

## Two findings

**The splitter has never split anything.**

| | |
|---|---|
| records in | 90 |
| chunks out | 90 |
| chunks with `part_idx > 0` | 0 |
| longest chunk | 314 characters |
| `CHUNK_SIZE` | 400 characters |

`split_text()` returns the whole string when it is shorter than the threshold,
and no Q&A pair in this corpus reaches 400 characters. `CHUNK_OVERLAP = 50` has
no effect on this system at all.

**The threshold is larger than the model's input window.** Measured with the
model's own tokeniser over all 90 chunks:

| | |
|---|---|
| model | `paraphrase-multilingual-MiniLM-L12-v2` |
| `max_seq_length` | 128 tokens |
| chunk tokens | 47 min · 113 max · 73.7 mean |
| chunks over the limit | 0 of 90 |
| longest chunk | 314 characters = 113 tokens |
| implied ratio | 2.78 characters per token |
| 128 tokens ≈ | 356 characters |
| `CHUNK_SIZE` | **400 characters** — 44 above what the model can read |

Nothing is being truncated today, because nothing is close to 400. But the
configuration permits a chunk the model cannot read. If one ever appears, its
tail is dropped before embedding, silently — sentence-transformers truncates
without raising. That chunk would then be findable only by its first half, while
still being displayed to the user in full.

## Why it matters even though nothing is broken

The two settings are inconsistent with each other, and nothing checks. The
character count and the token limit are measured in different units, so the
contradiction is invisible unless somebody converts between them — which is what
this script does.

## How to check

Run `python main.py 1` after any corpus change and read three lines:

- **chunks split** — still 0 means the stage is inert
- **longest chunk in characters** — approaching `CHUNK_SIZE` means it will start
- **longest chunk in tokens** — approaching 128 means truncation is beginning

## What to do

Set `CHUNK_SIZE` below the model's real ceiling — around 300 characters for this
model on Thai text. The current value promises something the model cannot
deliver.

Or use a model with a longer window. LAB04 uses `BAAI/bge-m3` at 8192 tokens,
which removes the constraint entirely.

Neither was changed here: the committed index and every number in `README.md`
were produced with the current settings.
