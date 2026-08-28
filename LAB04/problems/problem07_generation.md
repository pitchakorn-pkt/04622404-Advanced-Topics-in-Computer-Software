# Problem 07 — Retrieval hands over the right passage and the answer drifts

English · [ภาษาไทย](problem07_generation.th.md) · reproduce: `python main.py 7`

## What happens

From `outputs/eval_generation.json`, 20 questions:

| | |
|---|---|
| correct chunk retrieved | 0.9500 |
| answer carries a citation | 1.0000 |
| faithfulness | 0.7862 |
| **correctness** | **0.5957** |
| relevance | 0.6328 |

Retrieval did its job 95% of the time and every answer cited a source. The
remaining loss happens while the answer is being written.

One case was caught contradicting its own citation outright:

| | |
|---|---|
| chunk `[1]` supplied | เครื่องจะหยุดจ่ายไฟเมื่อแบตเต็ม |
| answer written | แม้แบตเต็มแล้วเครื่องยังจ่ายไฟเข้าแบต |

The answer cited `[1]` correctly by format and stated the opposite of it. Asking
again did not reproduce it, so this is not systematic — but it shows that a
citation number guarantees nothing about whether the sentence matches the source.

## The second problem: the metrics cannot see the first one

All three quality scores are word overlap:

```
faithfulness = word_overlap(answer, context)           eval_generation.py:78
correctness  = word_overlap(answer, reference_answer)  eval_generation.py:79
relevance    = word_overlap(query, answer)             eval_generation.py:80
```

They measure the proportion of shared words, not whether the meaning agrees. The
battery answer above shares nearly all its vocabulary with the chunk it
contradicts, so it scores *high* on faithfulness while being unfaithful.

So `faithfulness = 0.7862` should be read as "answers mostly use words from the
context", not "answers are faithful to the context". The metric is named after
something it does not measure.

## The tool that was built and never wired up

`JUDGE_PROMPT` (`prompt_templates.py:97`) is written and ready: it asks an LLM
to score an answer 1–5 against a named criterion and return JSON with a reason.

Grepping the project finds no file that imports or calls it. Evaluation is still
pure word counting.

It was left disconnected deliberately. Turning it on produces a new set of
numbers that could disagree with the ones already in `README.md` and in the
presentation slides, and the decision was to not change the reported figures
before submission. It is the first thing to do if this system is taken further.

## Lowest-faithfulness answers among those that retrieved correctly

| id | faithfulness | correctness | question |
|---|---|---|---|
| g0035 | 0.6757 | 0.5676 | สงสัยว่าเพื่อนบ้านมาเกาะสัญญาณของเรา ตรวจดูได้มั้ย |
| g0042 | 0.6809 | 0.5106 | อยากได้อะไรที่คนอื่นเดาไม่ออกแต่เราไม่ลืมเอง ควรตั้งแบบไหน |
| g0010 | 0.7273 | 0.6364 | เปิดโหมดถนอมพลังงานแล้วอยู่ได้นานขึ้นจริงหรือเปล่า ต้องแลกกับอะไร |

Low overlap here does not prove the answers are wrong — a good answer written in
its own words scores low too. That ambiguity is precisely why an LLM judge is
needed.

## What was fixed in this stage

**The `no_context` flag was always false.** Whenever chunks existed, the flag
said the system had answered, so callers could not distinguish an answer from a
refusal. It now derives from whether the LLM's refusal text appears
(`generator.py:99-102`).

**Prompt rules 2 and 3 contradicted each other.** Rule 2 said to reply with the
refusal message alone; rule 3 said to put `[n]` after every sentence that used a
source. The result was answers reading `ไม่พบข้อมูล [1][2][3]`. Rule 2 now
explicitly forbids citation numbers (`prompt_templates.py:16`).

**`NoLLM` split the prompt on English keys** while the prompt itself is Thai, so
the fallback path returned the wrong text. Both sides now use the same constants
(`prompt_templates.py:24-25`).

## How to check

Read `อัตราค้นเจอ chunk ที่ถูก` and `correctness` together. A high hit rate with
low correctness places the fault after retrieval. Then read the actual answers
against the chunks they cite — with word-overlap metrics, that reading cannot be
skipped.
