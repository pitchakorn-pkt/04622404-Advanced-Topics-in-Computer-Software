# Problem 06 — Nothing measures whether retrieval works

English · [ภาษาไทย](problem06_evaluation.th.md) · reproduce: `python main.py 6`

## What is missing

| | | |
|---|---|---|
| absent | `evaluation/` | scripts that measure |
| absent | `data/golden_set.json` | which chunk each question should return |
| absent | `evaluation/metrics.py` | MRR / hit@k / nDCG |
| absent | `outputs/eval_retrieval.json` | recorded results |

All four exist in LAB04, the next system built on the same template.

## What exists instead

`outputs/retrieval_results.json` holds four questions, from `SAMPLE_QUERIES`
hard-coded at `labs/lab07_complete_retrieval.py:24`. It records **what the
system returned**, not **whether what it returned was right**. With no answer
key to compare against, no score can be computed from it.

`data/sample_questions.txt` holds ten questions and no script opens it. Only the
README mentions it. The results reported there were produced by running the
system by hand and reading the output.

## Why it matters

**Not reproducible.** The reported figures cannot be re-checked with one
command; they have to be read again question by question.

**Not comparable.** Change the model, `CHUNK_SIZE`, or the corpus, and there is
no earlier number to say whether it got better or worse.

**One number hiding two facts.** Counting by hand tends to produce "5 correct
out of 10", which conceals that single-dish questions score 6/6 while cross-menu
questions score 0/4 and structurally cannot score higher — see
[problem 03](problem03_granularity.md).

## The smallest fix that would work

The corpus is 15 menus with the same six question shapes, so an answer key can
be generated: take each corpus question as the query and its own `chunk_id` as
the correct answer.

But that runs straight into the trap LAB04 found. Questions copied verbatim from
the corpus put every configuration at 1.0000, which separates nothing. A set of
hand-rewritten questions has to go alongside it. In LAB04 that set is 60
questions, and it is the only one that decides anything.
