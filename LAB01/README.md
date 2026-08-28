# LAB01 — LLM Data Pipeline

English · [ภาษาไทย](README.th.md)

**My part: Cleaning + Normalization** (stage 2), and later a local embedding
provider so the pipeline runs without a paid API key.

| File | |
|---|---|
| `Pipeline/cleaning.py` | `clean()` strips HTML, boilerplate and repeated lines; `normalize()` applies Unicode NFC, Thai digit and tone-mark folding, and whitespace cleanup |
| `Pipeline/02_data_cleaning.py` | runs the stage over every Collection output and prints a before/after sample |
| `Pipeline/outputs/cleaned_*.json` | result, 180 records |
| `Pipeline/outputs/boilerplate_lines.json` | the boilerplate the run detected |
| `Pipeline/embedding.py` | added `SentenceTransformersProvider`: `BAAI/bge-small-en-v1.5` through sentence-transformers, 384 dimensions, runs on this machine |
| `Pipeline/vector_store.py` | answers with Groq `llama-3.3-70b-versatile`; a query is embedded with whichever provider built the corpus |
| `main.py`, `requirements.txt`, `.env.example` | wiring and setup for the two above |

**From the team, used as input:** Collection (stage 1) — `Pipeline/01_data_collection.ipynb`
and `Pipeline/outputs/extracted_text_*.json`. Chunking (stage 3), metadata (stage 4)
and the scripts that drive the last two stages are the team's work as well: this
folder is a snapshot of the whole shared pipeline, not only of my part.

## Timeline

**2026-07-28 — Cleaning + Normalization** ([PR #1](https://github.com/Automatic28m/Advance-AI-RAG/pull/1), merged as `aca605e`)

`clean()` and `normalize()` are two functions that can be called on their own but
run one after the other. Two things came out of reading the real data instead of
the spec. The input arrives in two schemas, not one — Jobicy in camelCase with
integer ids, AIDevBoard in snake_case with UUID strings — both keyed on `id`. And
`jobExcerpt` had to be exempted from boilerplate removal: it repeats the opening
of `jobDescription`, which is usually a company blurb, so removing it emptied the
field on 30 of 160 records. Lines of four words or fewer are kept for a similar
reason — they are section headers, which the chunking stage uses as boundaries.
The schema notes went to the team as a comment on the PR.

**2026-07-31 — Local embedding and a free answering model** ([PR #11](https://github.com/Automatic28m/Advance-AI-RAG/pull/11), merged as `143068b`)

The team hit `HTTP 429` on the Gemini embedding quota, and `HTTP 404` on
`gemini-2.5-flash` from some keys, which left the last two stages unrunnable.
Embedding now runs locally by default and needs no key at all: 518 vectors in
about 13 seconds. The model is `BAAI/bge-small-en-v1.5` rather than the more
common MiniLM, because MiniLM's configured input limit is 128 tokens where bge
takes 512 — measured on this corpus, that silently truncated 72.7% of the chunks
against bge's 2.6%.

Answering moved to Groq's free tier, on `llama-3.3-70b-versatile` rather than
`llama-3.1-8b-instant`: over four test questions the 8b model copied a source
UUID one character wrong, which the citation check correctly flagged as invented.
Nothing was removed to make room — the Gemini and OpenAI providers are still
there as a fallback, and as the comparison for the report.

Two details cost time and are worth writing down. Groq answers `403`, not `404`,
when Cloudflare rejects the `Python-urllib/3.x` user agent (`error code: 1010`),
and this repository speaks HTTP through `urllib` alone; the fix was to send a
real `User-Agent`. And `post_with_retry` used to discard the response body, so
every failure looked the same from the outside — it logs the body now.

## Problems and fixes

Six problems found in this pipeline are written up in
[`problems/`](problems/) — what happens, why, how to check for it, and either
the fix applied or the reason none was. Each has a script that reproduces it
from the committed stage outputs:

```bash
cd problems && python main.py 0     # all six
```

Four of the six produce no error message at all, which is what makes a pipeline
of gracefully-degrading stages hard to debug.

## What the cleaning rule trades away

Boilerplate removal drops any line that appears in five or more documents, on the
reasoning that a line repeated across unrelated postings is a company blurb or an
equal-opportunity statement rather than part of the job. That reasoning holds only
if the postings are independent of each other, and in this corpus they are not:
Canonical accounts for 36 of the 160 Jobicy postings, Nebius for 9, Experian for 7
and iHerb for 5. One employer's postings repeat each other by nature, so their
lines cross a five-document threshold without being boilerplate at all.

Measured on the committed output, as the share of each employer's text that
survived cleaning:

| Employer | Postings | Text kept |
|---|---|---|
| the 58 employers with a single posting | 1 each | 86% |
| Experian | 7 | 86% |
| Canonical | 36 | 59% |
| iHerb | 5 | 34% |

The 77 lines in `outputs/boilerplate_lines.json` are mostly what the rule was
written for, but not all of them. `Experience with Linux (Debian or Ubuntu
preferred)` is in there, and so are `Experience with Microsoft Office Suite (Word,
Excel, PowerPoint)` and `Bachelor's Degree in Computer Science or related field
preferred` — requirements, removed from every posting that listed them. That
reaches the example query in this README: a search for who hires for Kubernetes
work is answered from postings whose stated Linux requirement is no longer in the
text.

Nothing here is the code doing something other than what it says. The threshold is
the assumption worth revisiting: counting the employers a line appears under,
rather than the documents, would separate a blurb repeated by many companies from
a requirement repeated by one. That is not changed here, because the cleaned
output is what the later stages were built and measured against.

Pulled with `git subtree` from [Automatic28m/Advance-AI-RAG](https://github.com/Automatic28m/Advance-AI-RAG), branch `Develop`.

---

# Advance Topics in Computer Software course
## Computer Engineering - RMUTT
## The purpose is to study the 8 steps of LLM data pipeline since Data Collection until the LLM / Retrieval to finally learn the methodology of RAG or Retrieval-Augmented Generation.
## Running it

Python 3.12. Embedding runs on this machine and needs no API key; only the last
step, where a model writes the answer, needs one.

```bash
pip install -r requirements.txt

python Pipeline/04_metadata.py     # annotate the chunks that are committed here
python Pipeline/05_embedding.py    # embed locally -- no key, around 13 seconds
python main.py --build             # index them into Pipeline/chroma_db
```

Then ask it something:

```bash
# retrieval only: prints the passages and what they scored. Needs no key.
python main.py --no-llm -q "which companies hire for Kubernetes"

# the same question, answered in prose with a citation on every claim
python main.py -q "which companies hire for Kubernetes"
```

The second one reads `GROQ_API_KEY` from `Pipeline/.env` (free key from
<https://console.groq.com/keys>); copy `Pipeline/.env.example` and fill it in.
Run `python main.py` with no `-q` to keep asking questions interactively.

`embeddings_*.json` and `chroma_*/` are derived, not source, so they are
gitignored. The three commands above rebuild them from what is committed, which
is why none of them cost anything.

To embed through an API instead of locally, pick a provider and give it its own
store -- vectors of different widths cannot share a collection:

```bash
python Pipeline/05_embedding.py --provider gemini --dimension 1536
python main.py --build --collection job_postings_gemini --persist-dir Pipeline/chroma_gemini
```

## Team members
- 116730462006-1 Phanlop Boonluea
- 116730462011-1 Saran Tanyavikai
- 116730462016-0 Sakda Baokam
- 116730462032-7 Praphavit Kaorak
- 116730462033-5 Praphakorn Pitamma
- 116730462035-0 Pitchakorn Phuadkhunthod
