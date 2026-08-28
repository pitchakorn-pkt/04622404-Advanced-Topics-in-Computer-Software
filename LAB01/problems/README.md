# LAB01 — Problems in this data pipeline, and what was done about them

English · [ภาษาไทย](README.th.md)

Six problems found in the LLM data pipeline in [`../`](../), covering the stages
from cleaning through to the answer that cites its sources.

A note on ownership: this folder is a snapshot of a shared team pipeline. The
Cleaning + Normalization stage and the local embedding provider are this
repository owner's part; Collection, Chunking and Metadata are teammates' work.
Problems 1, 2, 5 and 6 sit in the owned stages. Problem 3 sits *between* two
stages owned by different people, which is a normal place for this kind of
defect to live, and problem 4 is a property of how the last two stages fit
together.

Every number here was measured on the committed stage outputs. Each problem has
a script that reproduces it.

## Running it

```bash
cd LAB01/problems
python main.py        # menu
python main.py 3      # one problem
python main.py 0      # all six
```

Only problem 3 loads a model; the rest read the committed outputs and re-run the
real cleaning functions over them. Problems 4 and 6 extract the functions they
exercise directly from `vector_store.py` rather than importing it, because that
module imports `chromadb` — listed in `requirements.txt` but absent from the
shared `.venv`. The code being run is the real code either way.

## The six

| # | Problem | What was measured |
|---|---|---|
| [1](problem01_boilerplate.md) | Boilerplate over-removal | single-posting employers keep 100% of their text, iHerb keeps 41%; three of the 77 removed lines are stated requirements |
| [2](problem02_schemas.md) | Two schemas, one emptied field | camelCase/int vs snake_case/UUID; counting `jobExcerpt` as a document empties 30 of 160 |
| [3](problem03_truncation.md) | Token budget in the wrong units | chunking says 0 of 518 exceed 512; the model's own tokeniser says **163 of 518** |
| [4](problem04_dimension.md) | Vectors that cannot be compared | model and width are checked; **provider is assumed**, and a mismatch fails silently |
| [5](problem05_http.md) | Opaque network failures | urllib's User-Agent → 403; a retry that discarded the body; a model name the provider withdrew |
| [6](problem06_citations.md) | An invented citation | a UUID off by one character produces an answer that reads perfectly and cites nothing real |

## What connects them

Four of the six are failures with no error message: text removed by a rule that
was right in principle, a third of the corpus truncated below a ceiling that
looked safe, a provider mismatch that only makes scores meaningless, and a
citation that is well formed and points nowhere.

The two that were caught quickly were caught because something was instrumented
to say so out loud — the boilerplate set is written to a file on every run, the
truncation count is printed as a warning, and the invented-citation check is run
on every answer. That is the pattern worth keeping: in a pipeline of stages that
each degrade gracefully, the only defence is a stage that reports what it did.

## Where these appear elsewhere

Problem 3 has the same shape as the chunking problem in
[`../../LAB02/problems/`](../../LAB02/problems/) and
[`../../LAB04/problems/`](../../LAB04/problems/): a size setting expressed in
units the embedding model does not use. Problem 5's withdrawn model name is the
same Groq change that LAB04 hit and fixed.
