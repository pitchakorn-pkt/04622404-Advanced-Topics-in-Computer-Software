# Problem 08 — Settings that look like knobs but change what the system is

English · [ภาษาไทย](problem08_config.th.md) · reproduce: `python main.py 8`

## 1. The fusion weight is not a universal constant

Measured on the paraphrase variant, recorded in `config.py:82-87`:

| dense : BM25 | rerank off | rerank on | |
|---|---|---|---|
| 1 : 0 | 0.8961 | 0.9482 | no BM25 at all |
| 1 : 0.5 | 0.7219 | 0.9482 | current setting |
| 1 : 1 | 0.6967 | 0.9496 | textbook RRF |
| 1 : 1.5 | 0.6165 | 0.7583 | |
| 0 : 1 | 0.4953 | 0.7583 | BM25 only |

Read the "rerank off" column downwards: every increase in BM25 weight makes it
worse. Combining two retrievers is not automatically better than one. In this
corpus, questions and answers rarely share a distinctive exact term, so BM25 is
weak, and weighting it equally drags the merged ranking down.

A corpus full of model numbers, part codes or proper nouns would invert this.
The value has to be re-measured whenever the corpus changes and must never be
copied from somewhere else.

Why it is not simply set to 0: with reranking on, every value between 0 and 1
gives identical per-question results, because the reranker reorders the whole
candidate set anyway. The weight only matters when reranking is off.

## 2. A model name the provider withdrew, and nothing complained

```python
LLM_PROVIDER = "groq"
LLM_MODEL    = "openai/gpt-oss-120b"
LLM_PROVIDERS["groq"] = (..., "llama-3.3-70b-versatile", "GROQ_API_KEY")
```

`generator.py:23` reads `config.LLM_MODEL or default_model`. If `LLM_MODEL` is
ever empty, the system falls back to `llama-3.3-70b-versatile` — which Groq
removed on 18 August 2026. The default in that table is dead.

The failure is silent. `get_llm()` catches the exception and returns `NoLLM`
(`generator.py:69-74`), so the system keeps answering; the answers are just raw
corpus text with no model involved. Nothing errors.

**How to check:** grep an answer against the corpus file. An exact match means
the LLM is not running. Or watch for `[llm] Failed to use …` in the log.

**The rule that came out of this:** before every demo, confirm the LLM is
actually running. Do not take "an answer came out" as evidence.

## 3. A display switch that discards finished work

```python
SHOW_SOURCES = False
```

`Generator.build_sources()` (`generator.py:113-123`) builds the source list on
every answer — chunk id, question, source line, score. `main.py` then does not
print it, because this switch is off.

The user sees `[1]` and `[2]` in the answer with no way to learn what they refer
to, which defeats the entire reason for requiring citations.

## 4. One stage's default silently disables a feature in another

```python
USE_QUERY_TRANSFORM = False
USE_MEMORY = True
```

Conversation history reaches the query transformer only when
`USE_QUERY_TRANSFORM` is on (`rag_pipeline.py:61-62`), and it is off by default.

So `USE_MEMORY = True` affects answer writing and not retrieval. A follow-up
question like "แล้วอันไหนดีกว่ากัน" is sent to the retriever exactly as typed and
finds documents about something else.

Two ways of prepending the previous question were tried and measured; neither
improved anything, so the behaviour was kept and the limitation written into the
README rather than left silent.

## 5. Index staleness — checked live

```
daily_tech_qa.txt   194391 bytes
sha256              0615077beb9e7392bf4c7744aca4b6bb…
tracked settings    CHUNK_SIZE 400 · CHUNK_OVERLAP 50 · BAAI/bge-m3
```

`index_meta.find_problems()` compares the corpus hash and the three settings
that invalidate an index against what was recorded when it was built.

This originally compared file modification time. Git sets a fresh mtime on
checkout, so every clone was warned its index was stale when the file was
byte-identical. It now hashes the content (`index_meta.py:22-34`).
