# Problem 06 — An answer that cites a posting which does not exist

English · [ภาษาไทย](problem06_citations.th.md) · reproduce: `python main.py 6`

## The requirement

Every claim in an answer carries the tag of the passage it came from:

```
[jobicy_software_en:147496#2]     source : posting id # chunk index
```

One pattern, `CITATION_PATTERN` (`vector_store.py:97-104`), is used in both
places — to write the instruction given to the model, and to check what it wrote
back. They cannot drift apart.

## Three answers through the real checker

Passages offered to the model:

```
[aidevboard_ai:48720738-0f4b-483d-9739-14039ae457d0#0]
[jobicy_software_en:147496#2]
```

| answer | cited correctly | invented | verdict |
|---|---|---|---|
| correct citations | 2 | 0 | passes |
| UUID off by one character | 1 | **1** | caught |
| no citations at all | 0 | 0 | passes |

The caught tag is
`[aidevboard_ai:48720738-0f4b-483d-9739-14039ae457d1#0]` — the last character of
the UUID is `1` where the real posting ends in `0`.

## Why the second case is the dangerous one

The answer reads perfectly. The tag is well formed, the source is right, the
chunk index is right. Only the final character of a 36-character UUID is wrong.

Nobody reads a UUID, and nobody checks one by hand. Without an automated check
that answer passes as a good one while pointing at a posting that does not
exist. `answer()` reports it as `invented` (`vector_store.py:447`), which is
described in the code as the one failure that looks like a good answer.

## The gap that is still open

The third case — an answer with no citations at all — **passes**. The check asks
whether the tags written are real, not whether every claim carries one. An
answer that cites nothing is not caught by it.

## The design decision this produced

```
vector_store.py:79-84
# llama-3.1-8b was seen copying a UUID with one character wrong -- an answer
# that reads perfectly and cites a posting that does not exist. The invented
# check catches it, but a citation that has to be caught is not worth the speed.
DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"
```

`llama-3.1-8b-instant` was observed doing exactly this across four test
questions. The check caught it, and the conclusion was that a citation which has
to be caught is not worth the speed. The default moved to the larger model, and
the small one stayed available behind `--model`.

This is a case where a measurement changed the design rather than just reporting
a number.

## How to check

Read `invented` in the result of `answer()` every time. It should be empty, on
every question, always.

If one model produces it often, change the model rather than tuning the prompt —
copying a long string exactly is a property of the model, not of the
instructions.
