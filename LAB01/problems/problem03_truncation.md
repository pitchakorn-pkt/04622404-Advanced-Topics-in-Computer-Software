# Problem 03 — The token budget is counted in one tokeniser and spent in another

English · [ภาษาไทย](problem03_truncation.th.md) · reproduce: `python main.py 3`

## What the chunking stage believes

| | |
|---|---|
| chunks | 518 |
| counter used | tiktoken `cl100k_base` (`chunking.py:87-101`) |
| `token_count` recorded | 50 min · 500 max · 397.5 median |
| over 512 by that count | **0 of 518** |

The stage caps chunks at 500 tokens, comfortably under the 512 the embedding
model accepts. By its own numbers nothing is too long.

## What the model actually sees

Measured with `BAAI/bge-small-en-v1.5`'s own tokeniser, `max_seq_length = 512`:

| | |
|---|---|
| tokens per chunk | 43 min · 624 max · 404 median |
| over 512 | **163 of 518 = 31.5%** |
| tokens dropped | 2,955 |

The two counters are not the same counter. tiktoken is OpenAI's BPE; bge uses
BERT WordPiece. On the same text bge counts more — the worst chunk is 500 by
tiktoken and 624 by bge, a gap of 124 tokens.

So the budget is set in one unit and spent in another, and the 500-token ceiling
that looks safe is not.

This is an underestimate. `embedding_text()` prepends a header — job title,
company, location — before embedding, which eats more of the same budget and is
not deducted when chunks are sized. The header is read from `retrieval_metadata`,
added by `04_metadata.py`, whose output (`metadata_*.json`) is not committed, so
0 of 518 chunks carry it here. A full run truncates more than this.

## What it looks like when it happens

sentence-transformers truncates silently. The model simply stops reading and the
vector still comes back the right width — no error, nothing out of place.

What was cut was paid for in the chunking stage and is gone. The chunk becomes
findable by its opening only, while still being handed to the LLM in full when
it is used. What is searched and what is read are no longer the same text.

## What exists, and what is missing

`embedding.py:234-240` already counts and warns on every run:

```
WARNING: n/m texts are longer than 512 tokens and will be truncated
```

That is the right thing to do — it says so out loud rather than leaving it to be
discovered later as unexplained retrieval quality.

What is missing is anything that **prevents** it. The warning arrives after the
chunks have been built and paid for, and no stage reads it back to adjust the
ceiling.

## What would fix it

Have the chunking stage count with the same tokeniser the embedding stage will
use, instead of tiktoken as a proxy, and subtract the header length from the
budget.

If coupling the two stages is unwanted, lower the ceiling by the measured gap.
That works for this corpus and has to be re-measured whenever the model changes.

## A note on the figures in the lab README

The lab README records MiniLM truncating 72.7% of chunks against bge's 2.6% —
the measurement that chose bge in July 2026. Today's numbers do not match that
set, because the chunking stage changed afterwards and nothing re-measures it.

That is the same problem this page is about, one level up: a measurement decided
a design choice, and nothing re-checks the measurement.

## Whose stage is whose

Chunking is a teammate's stage; the cleaning stage and the local embedding
provider are this repository owner's part. The mismatch sits between the two, in
neither, which is a normal place for this kind of defect to live.
