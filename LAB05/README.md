# LAB05 — Every problem found in this course's systems, collected

English · [ภาษาไทย](README.th.md)

Three labs in this course built a working system: the shared data pipeline in
[`LAB01/`](../LAB01/), the Thai food Q&A retrieval system in [`LAB02/`](../LAB02/),
and the Thai retrieval-augmented Q&A system for phone and computer problems in
[`LAB04/`](../LAB04/). Each of them carries a `problems/` folder written while the
system was being built. This lab gathers all three in one place: **twenty-one
problems**, each with the cause, how to check for it, and either the fix applied
or the reason none was.

Everything in [`problems/`](problems/) is a copy of the write-up that lives with
its own system. The originals stay where they are — a problem belongs next to the
code it is about. What this folder adds is the view across all three at once,
which is where the repetitions show up.

## What is in here

| Set | System | Problems | Source |
|---|---|---|---|
| [`problems/lab01/`](problems/lab01/) | LLM data pipeline (team project, my stage: cleaning + normalization) | 6 | [`LAB01/problems/`](../LAB01/problems/) |
| [`problems/lab02/`](problems/lab02/) | RAG over a Thai food Q&A dataset | 6 | [`LAB02/problems/`](../LAB02/problems/) |
| [`problems/lab04/`](problems/lab04/) | RAG over Thai phone/computer problems | 9 | [`LAB04/problems/`](../LAB04/problems/) |

### LAB01 — the data pipeline

| # | Problem | What was measured |
|---|---|---|
| [1](problems/lab01/problem01_boilerplate.md) | Boilerplate over-removal | single-posting employers keep 100% of their text, iHerb keeps 41%; three of the 77 removed lines are stated requirements |
| [2](problems/lab01/problem02_schemas.md) | Two schemas, one emptied field | camelCase/int vs snake_case/UUID; counting `jobExcerpt` as a document empties 30 of 160 |
| [3](problems/lab01/problem03_truncation.md) | Token budget in the wrong units | chunking says 0 of 518 exceed 512; the model's own tokeniser says **163 of 518** |
| [4](problems/lab01/problem04_dimension.md) | Vectors that cannot be compared | model and width are checked; **provider is assumed**, and a mismatch fails silently |
| [5](problems/lab01/problem05_http.md) | Opaque network failures | urllib's User-Agent → 403; a retry that discarded the body; a model name the provider withdrew |
| [6](problems/lab01/problem06_citations.md) | An invented citation | a UUID off by one character produces an answer that reads perfectly and cites nothing real |

### LAB02 — Thai food Q&A retrieval

| # | Problem | What the system actually does |
|---|---|---|
| [1](problems/lab02/problem01_chunking.md) | Chunking | never runs — 90 records in, 90 chunks out; and `CHUNK_SIZE` 400 exceeds the model's 128-token window (≈356 characters) |
| [2](problems/lab02/problem02_metadata.md) | Metadata | menu name on all 90 chunks, read by zero live lines; 47 of 90 chunks have their nearest neighbour in a different menu, at cosine 0.93+ |
| [3](problems/lab02/problem03_granularity.md) | Retrieval granularity | one vector per Q&A pair: single-dish questions 6/6 on menu, cross-menu questions 0/4 and structurally unanswerable |
| [4](problems/lab02/problem04_topk.md) | Top-k / ranking | `main.py` hard-codes `top_k=1` over `config.TOP_K = 3`; a correct entry sat at rank 2, invisible |
| [5](problems/lab02/problem05_no_refusal.md) | No refusal | no threshold anywhere; out-of-scope questions score 0.21–0.38 against 0.56–0.83 in-scope, and that gap is never read |
| [6](problems/lab02/problem06_evaluation.md) | Evaluation | no answer key, no metrics, no harness; the ten test questions are opened by no script |

### LAB04 — Thai phone and computer problems

| # | Problem | What the system actually does | Status |
|---|---|---|---|
| [1](problems/lab04/problem01_hallucination.md) | Hallucination | never refuses — refusal rate 0.0000 over 20 questions | gated at `RELEVANCE_MIN = 0.50`, 0/60 false rejections |
| [2](problems/lab04/problem02_vocabulary.md) | Vocabulary mismatch | `otp` and `โอทีพี` are unrelated tokens; 13 of 50 loanwords mis-segmented | `SLANG_MAP` + a merged tokeniser dictionary |
| [3](problems/lab04/problem03_data_quality.md) | Data quality | parser drops malformed entries silently; a corpus can be false and still score full marks | domain replaced after 5 of ~15 facts proved wrong |
| [4](problems/lab04/problem04_chunking.md) | Chunking | has never run — 194 records in, 194 chunks out, longest 392 of 400 | documented, deliberately unchanged |
| [5](problems/lab04/problem05_metadata.md) | Metadata | `category` on all 194 chunks, read by zero files on the retrieval path | open — two options, both costed |
| [6](problems/lab04/problem06_reranking.md) | Re-ranking | hit@1 0.6333 → 0.9333 while hit@10 barely moves | reranking on; 20 ms → 490 ms |
| [7](problems/lab04/problem07_generation.md) | Faithfulness | 95% correct retrieval, 0.5957 correctness; one answer contradicted its own citation | 3 prompt/flag bugs fixed; `JUDGE_PROMPT` still unwired |
| [8](problems/lab04/problem08_config.md) | Configuration | fusion weight is corpus-specific; a withdrawn model degrades silently | measured table in `config.py`; index check now hashes content |
| [9](problems/lab04/problem09_evaluation.md) | Evaluation | 4 of 5 question variants sit at 1.0000 and separate nothing | `paraphrase` used throughout; `usable` flag added |

## Running it

Every problem has a script that reproduces it from artefacts already committed to
this repository. From a fresh clone:

```bash
cd LAB05
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd problems
python main.py                     # menu
python main.py lab04               # one set — all nine LAB04 problems
python main.py lab04 6             # one problem
python main.py 0                   # all twenty-one
```

Each set can also be run on its own from inside its folder, exactly as it is run
in its home lab — `cd problems/lab02 && python main.py 0`.

Two things to know. The scripts read the stage outputs, indexes and source files
that live under `LAB01/`, `LAB02/` and `LAB04/`; they do not carry copies of the
data, so those folders have to be present. And six of the twenty-one load an
embedding model — LAB01 problem 3 and LAB02 problems 1 to 5 — which downloads
`paraphrase-multilingual-MiniLM-L12-v2` on first run. The other fifteen, all nine
of LAB04 among them, read committed files and re-run the real functions over them.

## What the collection shows

Laid side by side, the same defect keeps reappearing in systems that were built
months apart, from different templates, over different corpora.

**Chunking that never runs.** LAB02 problem 1 and LAB04 problem 4 are the same
finding: records in equals chunks out, because every record is already shorter
than `CHUNK_SIZE`. LAB01 problem 3 is its other half — a size limit expressed in
characters while the model counts tokens, so the ceiling that looked safe let
163 of 518 chunks be truncated. Three systems, one habit: a size setting written
in units the embedding model does not use, and no assertion that the stage did
anything.

**Metadata written and never read.** LAB02 problem 2 and LAB04 problem 5 both
attach a category to every chunk and then never consult it on the retrieval path.
In LAB02 that is measurable harm: 47 of 90 chunks have their nearest neighbour in
a different menu.

**Evaluation arriving last, and then saturating.** LAB02 problem 6 has no harness
at all; LAB04 problem 9 has one whose questions were copied out of the corpus, so
four of five variants score 1.0000 and separate nothing. A test set that cannot
fail is the same blind spot as no test set, arrived at from the other direction.

**Answering when there is nothing to answer from.** LAB02 problem 5 and LAB04
problem 1 are the same missing threshold. In both systems the score gap between
in-scope and out-of-scope questions was already there in the numbers; nothing read
it.

**Most of these produce no error message.** Of the twenty-one, the ones that were
caught early were caught because something was instrumented to say what it had
done out loud — the boilerplate set written to a file on every run, the truncation
count printed as a warning, the citation check run on every answer. That is the
pattern worth carrying into the final project.

One more repetition that is not a design defect: LAB01 problem 5 and LAB04
problem 8 are both the same withdrawn Groq model name, hit twice in two systems.

## What this lab does not establish

No new measurement was made here. Every number on this page is the one measured
in its own lab, on that lab's data, and it is reproduced by the same script; this
folder adds the cross-reading, not evidence.

The three sets are copies. If a write-up is corrected in `LAB01/problems/`,
`LAB02/problems/` or `LAB04/problems/`, the copy here does not follow on its own.

And twenty-one problems from three systems built by one student over one term is
not a survey of anything. The repetitions above are worth taking seriously as
habits of the person who wrote them, which is what the exercise is for — they are
not a claim about RAG systems in general.
