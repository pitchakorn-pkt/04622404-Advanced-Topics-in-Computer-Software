# Problem 04 — Vectors made differently cannot be compared

English · [ภาษาไทย](problem04_dimension.th.md) · reproduce: `python main.py 4`

## The requirement

Retrieval compares a query vector against stored vectors. That comparison means
something only if both came from the same **provider**, **model** and
**dimension**. A vector does not say which made it — 384 floats from bge and 384
floats from Gemini look identical — so the pipeline has to carry that
information itself.

## Two guards that exist

**`embedding_settings()`** (`vector_store.py:140-150`) asserts that every record
in a collection records the same model and the same width. Running it on mixed
input:

| input | result |
|---|---|
| all matching | passes — `BAAI/bge-small-en-v1.5` · 384 |
| two models | stops — `records were embedded with several models: [...]` |
| two widths | stops — `records have several dimensions: [384, 1536]` |

**The collection width.** `create_collection()` writes the dimension into the
collection metadata (`vector_store.py:232-233`) and `upsert()` checks every
batch against it (`vector_store.py:248-255`). Chroma does not enforce a width
schema itself, so 1536-wide vectors going into a 384 collection would not be
rejected on their own.

This is why switching provider needs a separate collection:

```bash
python Pipeline/05_embedding.py --provider gemini --dimension 1536
python main.py --build --collection job_postings_gemini \
                       --persist-dir Pipeline/chroma_gemini
```

## The gap that remains

Provider is **assumed**, not checked. `vector_store.py:64` records what a
collection is taken to have been embedded with when it does not say.

A collection built with a different provider whose width happens to match passes
both guards above, and retrieval then runs with no error at all. The result is
not a failure — it is meaningless similarity scores, because two unrelated
vector spaces are being measured against each other. The output looks like an
ordinary set of results.

That is the harder failure of the two. A width mismatch breaks the upsert and is
visible immediately; a provider mismatch breaks nothing and only makes the
answers worse.

## How to check

Ask a question whose answer you already know. If the top score is unusually low
and the results are unrelated to the question, suspect this before suspecting
corpus quality — then compare the collection metadata against what the records
themselves record.

## What would fix it

Write the provider into the collection metadata the same way the dimension is,
and compare it at query time. Turn the assumption into a check.

## Running note

`vector_store.py` imports `chromadb`, which is in `LAB01/requirements.txt`
(`chromadb==1.5.9`) but is not installed in the shared `.venv` this repository
uses for the other labs. The script therefore extracts the real
`embedding_settings()` from the source file and runs that, rather than importing
the module — the code being exercised is the actual code, not a copy.
