# Problem 05 — No way to say the corpus does not cover this

English · [ภาษาไทย](problem05_no_refusal.th.md) · reproduce: `python main.py 5`

## What happens

There is no score threshold anywhere in LAB02. Asked about things the corpus has
nothing on, the system answers anyway:

| question | top-1 score | returned |
|---|---|---|
| พาสต้าคาโบนาราทำยังไง | 0.3821 | [ยำวุ้นเส้น] วิธีทำยำวุ้นเส้นโดยย่อ |
| ราคาตั๋วเครื่องบินไปเชียงใหม่ | 0.2831 | [ข้าวซอย] ข้าวซอยเป็นอาหารภาคไหน |
| สวัสดีครับ | 0.2096 | [ขนมครก] ขนมครกเผ็ดไหม |
| 2+2 เท่ากับเท่าไหร่ | 0.2427 | [ผัดกะเพราหมูสับ] ผัดไทยกับผัดกะเพราใช้เส้น… |

## The good news: the scores do separate

| group | lowest | highest |
|---|---|---|
| single-dish questions | 0.6855 | 0.8279 |
| cross-menu questions | 0.5559 | 0.7312 |
| out of scope | 0.2096 | 0.3821 |

In-scope and out-of-scope do not overlap — they are 0.3033 apart. A threshold
around 0.45–0.53 separates every question in this sample. The information needed
to refuse is already in the score; nothing reads it.

Cross-menu questions are the hard group. They are genuinely in-domain, so their
scores are not low, yet the answer returned is still wrong. No single threshold
handles them — that is a structural limit, not a scoring one. See
[problem 03](problem03_granularity.md).

## Why

`retriever.retrieve()` returns the nearest `top_k` always, dropping only
`idx == -1`, which happens when the index holds fewer vectors than `top_k`
(`retriever.py:31-33`).

`main.py:64-66` has a branch that prints
`No relevant answer found in the knowledge base` when `results` is empty. With
90 vectors in the index and `top_k=1`, `results` is never empty. That message
cannot be reached.

## How to check

Ask three or four questions the corpus certainly does not cover and read the
top-1 score. If it lands in the same range as real questions, the score cannot
be used as a gate. If it sits clearly below, a gate is both possible and worth
adding.

## What to do

Compare the top-1 score against a threshold before printing, and say the corpus
does not cover it rather than showing an unrelated dish.

LAB04 does this at `serve.py:35` with a cutoff of 0.50, derived from 60 real
questions against 20 written to fall outside — 0 of 60 falsely rejected.

The four out-of-scope questions here are too few to set a real threshold. Twenty
or so would be needed first, and they have not been written.
