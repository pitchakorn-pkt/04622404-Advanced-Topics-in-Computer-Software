# LAB02 — Problems in this retrieval system, and what could be done

English · [ภาษาไทย](README.th.md)

Six problems found in the Thai food Q&A retrieval system in [`../`](../). Each
is written up with what happens, why, how to check for it, and what a fix would
cost.

A note on ownership: the code in `src/` and `labs/` is the lab template
unchanged. What this lab contributed is the 90-pair Thai food corpus. So these
are problems in the system as it stands, not a list of mistakes made while
building it — and several of them are inherited defaults that the template's own
comments left switched off.

Every number here was measured on this system. Each problem has a script that
reproduces it.

## Running it

```bash
cd LAB02/problems
python main.py        # menu
python main.py 3      # one problem
python main.py 0      # all six
```

Problems 1 and 3–5 load the embedding model, because reproducing them means
encoding a query the corpus has never seen. It is the same model `main.py` uses
and it is loaded once and shared. Problems 2 and 6 read committed files only.

## The six

| # | Problem | What the system actually does |
|---|---|---|
| [1](problem01_chunking.md) | Chunking | never runs — 90 records in, 90 chunks out; and `CHUNK_SIZE` 400 exceeds the model's 128-token window (≈356 characters) |
| [2](problem02_metadata.md) | Metadata | menu name on all 90 chunks, read by zero live lines; 47 of 90 chunks have their nearest neighbour in a different menu, at cosine 0.93+ |
| [3](problem03_granularity.md) | Retrieval granularity | one vector per Q&A pair: single-dish questions 6/6 on menu, cross-menu questions 0/4 and structurally unanswerable |
| [4](problem04_topk.md) | Top-k / ranking | `main.py` hard-codes `top_k=1` over `config.TOP_K = 3`; a correct entry sat at rank 2, invisible |
| [5](problem05_no_refusal.md) | No refusal | no threshold anywhere; out-of-scope questions score 0.21–0.38 against 0.56–0.83 in-scope, and that gap is never read |
| [6](problem06_evaluation.md) | Evaluation | no answer key, no metrics, no harness; the ten test questions are opened by no script |

## What connects them

Five of the six are things that are present but unused, or configured but inert.
The chunk-size setting has no effect, the menu name is never read, `TOP_K` is
overridden, the score that could refuse is never compared to anything, and the
test questions are never run. The system works, and most of what was built for
it does not participate.

Problem 3 is different in kind. It is not something switched off — it is a limit
of the structure chosen, and no setting reaches it.

## How this relates to the other labs

LAB04 is the next system built on the same template, and it fixes or measures
most of what is listed here: it adds reranking (problem 4), a relevance gate
(problem 5), and a full evaluation harness (problem 6). It does **not** fix
problems 1 and 2 — the chunking stage is inert there too, and its category field
is equally unused. Those two are documented in
[`../../LAB04/problems/`](../../LAB04/problems/).
