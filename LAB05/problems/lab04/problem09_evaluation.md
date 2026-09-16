# Problem 09 — The measurement is the part most likely to lie

English · [ภาษาไทย](problem09_evaluation.th.md) · reproduce: `python main.py 9`

Every number quoted in the other eight problems comes from these files. This one
asks whether they can be trusted, and shows four ways they nearly could not be.

## 1. Four of the five question variants decide nothing

MRR by variant, all four retrieval settings, 60 questions:

| variant | dense_only | bm25_only | hybrid | hybrid+rerank |
|---|---|---|---|---|
| verbatim | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| slang | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| partial | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| natural | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **paraphrase** | **0.8961** | **0.4953** | **0.7219** | **0.9482** |

The top four rows are identical across every setting, including `bm25_only`,
the weakest by a wide margin. Reading only those rows leads to "all
configurations are equally good", which is false.

They are generated from the corpus questions with small edits, leaving word
overlap with the original at 1.00 / 1.00 / 0.99 / 0.86 — so retrieval reduces to
matching the same words back. `paraphrase` was rewritten by hand for all 60
questions, down to 25% average overlap.

`paraphrase` is the only row that separates anything, and the only one reported
anywhere.

**A test set on which every configuration scores full marks does not mean the
system is good. It means the test set cannot measure.**

## 2. The evaluator once skipped a step the real system performs

`main.py` calls `normalize_query()` before every search. The original
`eval_retrieval` passed raw questions straight through, so it reported numbers
lower than the running system produced. Fixed at
`evaluation/eval_retrieval.py:74-76`.

A second bug in the same file: `all_misses` was overwritten on each pass, so only
the last configuration survived and misses could not be compared across
settings.

Both had the same signature — the output looked plausible, so nobody questioned
it. The way to catch this is to walk the evaluator's path and the real path side
by side and check they pass through the same stages.

## 3. A stage that failed on every call reported plausible numbers

What is committed in `outputs/eval_query_transform.json`:

| configuration | MRR (paraphrase) | llm_calls | failures | usable |
|---|---|---|---|---|
| raw | 0.9482 | 0 | 0 | True |
| normalize_no_slang | 0.9482 | 0 | 0 | True |
| normalize | 0.9482 | 0 | 0 | True |

There are no rows for the LLM-based modes — `rewrite`, `multi_query`, `hyde`.
All three remain unmeasured, so there is nothing to report for them.

`QueryTransformer.transform()` catches exceptions and quietly returns the
original query (`query_transform.py:147-149`). That is correct for production:
one stage failing should not take the system down.

During evaluation it became a trap. The free Groq quota ran out, so every LLM
call failed, and the evaluator measured *the untransformed question* 60 times
and reported the result as that mode's score. The numbers came out plausible
while the stage under test was doing nothing at all.

The fix wraps the LLM in `CountingLLM`
(`evaluation/eval_query_transform.py:27`), which counts `llm_calls` and
`llm_failures` and sets `usable = (failures == 0)` (lines 124-126). Any row with
`usable = false` must not be cited.

**The principle: any stage that degrades gracefully in production must fail
loudly under measurement. Otherwise you get numbers for something that never
ran.**

## 4. Limits that no code change can remove

The corpus and the test questions were written by the same person, who asks
questions inside the same frame of mind that produced the answers. Every number
here is an upper bound, not what a real user should expect. The fix is to have
someone else write the test questions, and it has not been done.

60 test questions against a 194-pair corpus means a difference of one or two
questions is within chance. Significance has to be read alongside:

| comparison | per-question record | p | reading |
|---|---|---|---|
| mixing BM25 hurts | dense 14 : hybrid 1 | 0.0009 | conclusive |
| reranking helps | 0 : 18 | < 0.001 | conclusive |
| dense vs hybrid+rerank | 0 : 5 | 0.063 | a trend only |

The useful statistic is **the number of questions that flip**, not the average.
Growing the corpus from 172 to 194 pairs barely moved the averages — misses went
from 3 to 4 — while the number of questions that flip between configurations
widened and p improved by an order of magnitude.
