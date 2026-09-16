# Problem 01 — Answering when the corpus has nothing to say

English · [ภาษาไทย](problem01_hallucination.th.md) · reproduce: `python main.py 1`

## What happens

Across the 20 questions in `outputs/eval_generation.json` the system refused
exactly zero times. One of those questions retrieved no correct chunk at all and
was still answered in full, with a citation attached.

| | |
|---|---|
| questions measured | 20 |
| refusal rate | 0.0000 |
| correct chunk retrieved | 0.9500 |
| correctness | 0.5957 |

The gap between a 0.95 retrieval rate and a 0.60 correctness score is answers
written on evidence that did not support them.

## Why

Two guards exist and neither one fires.

`generator.py:84-89` returns `NO_CONTEXT_MESSAGE` when `chunks` is empty. It
never is. FAISS answers a nearest-neighbour query, and a nearest neighbour
always exists — `vector_store.py:44` returns the closest `top_k` vectors for any
input, related or not. The empty-context branch is unreachable in normal
operation.

Rule 2 of `SYSTEM_PROMPT` (`prompt_templates.py:16`) instructs the model to
refuse when the evidence is thin. That is a request written in Thai prose, not a
constraint. Whether it is honoured is the model's decision, and on these 20
questions it was never taken.

So the system had no mechanism for "I don't know" — only a suggestion.

## How to check

Ask something the corpus certainly does not cover and see whether an answer
comes back. In the committed measurements, watch two fields together in
`outputs/eval_generation.json`:

- `อัตราการตอบว่าไม่รู้` — the refusal rate
- `อัตราค้นเจอ chunk ที่ถูก` — the retrieval hit rate

Read alone, neither shows the problem. A refusal rate of zero looks like
confidence; a hit rate of 0.95 looks like success. The pair is what exposes it.

## What was done

`serve.py:35` adds a relevance gate ahead of the LLM. It compares the cosine of
the top dense hit against a fixed floor and, below it, stops: no retrieval, no
context, no pretending.

```
RELEVANCE_MIN = 0.50
```

The floor was measured, not guessed — 60 real questions from
`data/eval_paraphrases.txt` against 20 written to fall outside the corpus:

| | |
|---|---|
| real questions, lowest score | 0.5071 |
| real questions, median | 0.6469 |
| false rejections at 0.50 | 0 of 60 |
| out-of-corpus caught at 0.50 | 13 of 20 |

The score has to come from the dense retriever. The reranker's score cannot be
used as a threshold: a cross-encoder is trained to order candidates, not to
calibrate confidence, and it rates `"ช่วยหน่อย"` at 0.8161 and `"hello"` at
0.7271 while giving some genuine questions 0.0012. See
[problem 06](problem06_reranking.md).

Below the floor the question is still answered, but by a general-purpose prompt
in a separately labelled box (`GENERAL_PROMPT`, `serve.py:38`), so a viewer can
see the answer did not come from the corpus.

## What is still open

Seven of the 20 out-of-corpus questions score above the floor. They are broad
questions that belong to the domain but name no symptom:

| question | dense score |
|---|---|
| โทรศัพท์พังทำยังไงดี | 0.6457 |
| คอมมีปัญหา | 0.6231 |

Rejecting these would be wrong — they are in scope. The right response is to ask
what the symptom is. The system has no clarifying-question path, so for now it
answers them from whichever three chunks happen to sit closest.
