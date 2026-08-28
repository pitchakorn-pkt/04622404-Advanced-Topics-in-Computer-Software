# Problem 06 — Retrieval finds it and ranks it too low

English · [ภาษาไทย](problem06_reranking.th.md) · reproduce: `python main.py 6`

## What happens

All four settings, 60 questions, paraphrase variant — the only one that
separates anything (see [problem 09](problem09_evaluation.md)):

| setting | MRR | hit@1 | hit@10 | ms/query |
|---|---|---|---|---|
| dense_only | 0.8961 | 0.8500 | 0.9833 | 21.9 |
| bm25_only | 0.4953 | 0.4000 | 0.6667 | 0.2 |
| hybrid | 0.7219 | 0.6333 | 0.9500 | 20.2 |
| hybrid+rerank | **0.9482** | **0.9333** | 0.9833 | 489.8 |

The whole problem is in two of those numbers. Adding reranking moves hit@10 from
0.9500 to 0.9833 — almost nothing. It moves hit@1 from 0.6333 to 0.9333 — a
great deal.

The right document was already in the top ten nearly every time. Retrieval was
not failing to find it. It was failing to order it. And `TOP_K = 3`, so anything
at rank 5 is invisible to the user regardless.

## Why

The first stage uses a bi-encoder. Query and document are encoded separately —
the documents at index-build time, long before anyone asks anything — and
compared by distance. It is good at "these are about the same subject" and weak
at "this one answers that question", because it never sees the two together.

RRF (`hybrid_retriever.py:59-77`) does not help with this. It merges by rank
position only and never looks at content at all.

A cross-encoder scores query and document as one input, so it can judge the pair
directly. That is why it fixes ordering and barely changes recall.

## A case that reproduces exactly

Question: **"มือถือตกน้ำต้องทำอะไรก่อน"**

After RRF:

| rank | score | chunk | |
|---|---|---|---|
| 1 | 0.02407 | 16 | มือถือช้าลงมาก ควรทำอะไรก่อน |
| 5 | 0.02264 | 90 | เครื่องโดนน้ำ ควรทำอะไรทันที ← correct, invisible at `TOP_K = 3` |

After reranking:

| rank | score | chunk | |
|---|---|---|---|
| 1 | 0.718 | 90 | เครื่องโดนน้ำ ควรทำอะไรทันที |

The two chunks are in different categories — see
[problem 05](problem05_metadata.md). This case is what the jump from 0.7219 to
0.9482 looks like on one question.

## The cost

| | |
|---|---|
| per query | 20.2 ms → 489.8 ms (24×) |
| model size | +2.2 GB, loaded at startup |

Still worth it: the LLM takes around 1.4 s to write the answer, so half a second
of reranking is a minority of what the user actually waits for.

## The trap: this score cannot be a threshold

A cross-encoder is trained to order candidates, not to calibrate confidence. Its
scores are meaningful within one query and meaningless across queries:

| input | rerank score |
|---|---|
| `"ช่วยหน่อย"` | 0.8161 |
| `"hello"` | 0.7271 |
| some genuine questions | 0.0012 |

The best rerank-based cutoff tried still falsely rejected 4 of 60 real
questions. The corpus-scope gate in [problem 01](problem01_hallucination.md)
therefore uses the dense cosine, where 0.50 gives 0 of 60 false rejections.

## How to check whether the stage earns its cost elsewhere

Look at the gap between hit@1 and hit@10 **before** reranking.

- **Wide gap** — found but badly ordered. Reranking will help a lot.
- **Narrow gap** — not found in the first place. The fix belongs in the
  embedding model or the corpus, and reranking will change little.
