# Problem 04 — One result shown, and nothing reordering it

English · [ภาษาไทย](problem04_topk.th.md) · reproduce: `python main.py 4`

## What happens

```python
# main.py:61   # results = retriever.retrieve(query, top_k=config.TOP_K)
# main.py:62   results = retriever.retrieve(query, top_k=1)
```

`config.TOP_K` is 3. The line that would read it is commented out and replaced
with a literal 1, so changing `TOP_K` has no effect on `main.py` at all. Both
lines come from the lab template and were not changed here.

The cost, measured over the six single-dish questions:

| question | rank 1 | the matching entry |
|---|---|---|
| ข้าวซอยเป็นอาหารภาคไหน | ข้าวซอยใส่อะไรบ้าง · 0.7448 | rank 2 · 0.7113 |

One of six. The score gap is 0.0335 — too small to treat rank 1 as meaningfully
better than rank 2. With `top_k=1` the user never sees the entry the system
already found.

## Why nothing corrects it

The whole system is one stage: encode the query, search FAISS
(`retriever.py:27-28`). There is no BM25, no RRF, no cross-encoder.

A bi-encoder encodes query and document separately, so it is good at "these are
about the same subject" and weak at "which of these answers the question". That
is exactly the ข้าวซอย failure: both entries are about ข้าวซอย, so the one asking
about *region* does not stand out.

LAB04 added that second stage and measured it: hit@1 moved 0.6333 → 0.9333 while
hit@10 barely changed — the same symptom seen here, quantified.

## What to do, cheapest first

1. **Read `top_k` from config and show all three with their scores.** One line,
   no rebuild, and the user picks the one that matches.
2. **Uncomment the matched-question display (`main.py:31`) as well** — otherwise
   three results are three indistinguishable blocks of text.
3. **Add a cross-encoder as LAB04 does.** Most effective and most expensive:
   +2.2 GB of model and roughly 24× the time per query.
