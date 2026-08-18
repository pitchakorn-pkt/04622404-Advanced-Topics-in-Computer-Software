# LAB04 — RAG System Development I

English · [ภาษาไทย](README.th.md)

A Thai-language RAG system that answers everyday phone and computer questions.
It builds on the DL-04 lab template: the knowledge base was replaced with a corpus
written for this assignment, and the parts of the pipeline that handle Thai text were
reworked and measured rather than assumed.

The assignment allows any domain, which raises a question worth answering properly:
Thai is said to be the harder choice because word segmentation and filtering are weaker
than in English. This lab keeps Thai and asks whether that is actually true, or whether
the defaults were simply wrong for the language. Every claim below is backed by a number
that can be reproduced from the files in this folder.

The short answer is that the language was not the problem. Retrieval improved from
MRR 0.5427 to 0.9482 on the hardest question set. The single largest factor was the
embedding model, not tokenization. Filtering Thai stopwords — the intuitive fix —
made results 21% worse, not better.

## Structure

```text
LAB04/
│
├── data/
│   ├── daily_tech_qa.txt                   # knowledge base, 194 Q&A pairs in 10 categories
│   ├── eval_paraphrases.txt                # 60 hand-written test questions
│   └── golden_set.json                     # generated evaluation set
│
├── outputs/
│   ├── extracted_text.json                 # parsed Q&A pairs with line numbers
│   ├── chunks.json                         # 194 chunks with metadata
│   ├── embeddings.npy                      # embedding vectors
│   ├── retrieval_results.json              # top-k results from lab07
│   ├── eval_retrieval.json                 # retrieval scores per configuration
│   ├── eval_query_transform.json           # scores for the query-preparation stage
│   └── eval_generation.json                # answer quality scores
│
├── vector_db/
│   ├── document.index                      # FAISS index, dense semantic search
│   ├── bm25_index.pkl                      # BM25 index, exact-token search
│   ├── chunk_store.json                    # chunks aligned with FAISS order
│   └── index_meta.json                     # fingerprint of the corpus the index was built from
│
├── labs/
│   ├── lab01_extract_text.py               # extract text from the source file
│   ├── lab02_chunking.py                   # split text into chunks
│   ├── lab03_create_embeddings.py          # generate embeddings
│   ├── lab04_create_vector_db.py           # build the FAISS database
│   ├── lab05_query_embedding.py            # create query embeddings
│   ├── lab06_similarity_search.py          # retrieve top-k chunks
│   └── lab07_complete_retrieval.py         # complete retrieval pipeline
│
├── src/
│   ├── document_loader.py                  # file loading and text extraction
│   ├── text_splitter.py                    # text chunking
│   ├── thai_text.py                        # Thai normalisation and tokenisation (added)
│   ├── embedding_model.py                  # embedding model
│   ├── vector_store.py                     # FAISS vector database
│   ├── index_meta.py                       # detect when the index is stale
│   ├── retriever.py                        # dense-only retrieval
│   ├── hybrid_retriever.py                 # BM25 + dense + weighted RRF fusion
│   ├── rerankers.py                        # cross-encoder reranking
│   ├── query_transform.py                  # query rewrite, multi-query, HyDE
│   ├── prompt_templates.py                 # prompt templates
│   ├── generator.py                        # LLM answer generation
│   ├── memory.py                           # conversation history
│   └── rag_pipeline.py                     # end-to-end pipeline
│
├── evaluation/
│   ├── metrics.py                          # Hit@k, Recall@k, Precision@k, MRR, nDCG
│   ├── build_golden_set.py                 # generate the evaluation set
│   ├── eval_retrieval.py                   # compare retrieval configurations
│   ├── eval_query_transform.py             # compare query-preparation modes (added)
│   └── eval_generation.py                  # evaluate answer quality
│
├── config.py                               # project configuration
├── build_index.py                          # build all indexes
├── requirements.txt                        # dependencies (added)
├── main.py                                 # run the system
├── serve.py                                # local web demo, standard library only (added)
└── web/
    └── index.html                          # the demo's single page (added)
```

## The knowledge base

194 Thai question-answer pairs across ten categories: battery and charging, slow devices
and full storage, internet and Wi-Fi, accounts and passwords, scams and security, data and
backups, apps and updates, display and audio and camera, buying and maintaining devices,
and documents and everyday tasks. The file format follows the template.

```
[หมวด: มิจฉาชีพและความปลอดภัย]
Q: รหัสโอทีพีบอกใครได้บ้าง
A: ไม่มีใครเลย ไม่ว่าจะอ้างเป็นธนาคาร เจ้าหน้าที่ ตำรวจ หรือฝ่ายบริการลูกค้า ...
```

The domain was chosen for two reasons. It covers questions ordinary people actually ask,
and its answers are procedural advice rather than specifications. The second reason
matters more than it appears: an earlier version of this lab used an embedded-systems
corpus, and checking roughly fifteen of its specific figures against vendor documentation
found five errors. A corpus whose facts are wrong produces wrong answers while every
retrieval metric still reports success, which makes the errors invisible to the evaluation.

The corpus deliberately contains topics that sit close enough together to be confusable:
a slow device because storage is full, because too many programs start at boot, or because
of a recent update; syncing versus backing up; clearing a cache versus clearing app data
versus resetting the device.

## How to run

```bash
pip install -r requirements.txt
python build_index.py       # builds FAISS + BM25; first run downloads about 2.2 GB
python main.py              # interactive question answering
python serve.py             # the same pipeline as a web page on 127.0.0.1:8000
```

Reranking is on by default, so `main.py` downloads a further 2.2 GB on first use.
Answer generation needs `GROQ_API_KEY`. Without a key the system still runs — set
`USE_LLM = False` in `config.py` and it returns the retrieved text directly. Every switch
lives in section 1 of `config.py` and can be toggled and re-measured immediately.

Evaluation is split across four scripts: `evaluation.build_golden_set` produces the test
set, `evaluation.eval_retrieval` compares retrieval configurations,
`evaluation.eval_query_transform` measures the query-preparation stage, and
`evaluation.eval_generation` scores answer quality. The last two need a key.
`evaluation.metrics` also carries a self-test of the metric formulas against
hand-computed values.

## The web demo

`serve.py` puts the pipeline `main.py` runs behind a single page, to make the retrieval
stages visible rather than to add capability. Every answer lists the chunks behind it with
the score each stage gave them, the configuration can be switched between dense, hybrid,
and hybrid + rerank between questions, and the order the fusion produced is shown beside
the order the cross-encoder returned, so it is clear which chunk the reranking moved.

Nothing under `src/` was changed for it. `config.USE_HYBRID` is read inside `retrieve()`
rather than at import, and reranking depends on whether the retriever holds a reranker, so
both can be set for one request and restored afterwards. The page uses the standard
library only and adds no dependency.

### Refusing what the corpus cannot answer

The retriever returns `TOP_K` chunks for every query, related or not, and rule 2 of the
system prompt asks the model to refuse when the context is insufficient. It almost never
does. Asked whether it would rain today, the system answered with the entry about a phone
dropped in water and reported no refusal.

The demo therefore checks the corpus before answering. It measures the cosine of the
nearest chunk, and below 0.50 treats the question as outside the corpus: the answer becomes
the refusal message, and a separately labelled block carries a general answer from the LLM
that cites nothing.

The threshold was measured against the 60 hand-written test questions and 20 out-of-corpus
questions written for the purpose.

| gate | real questions refused wrongly | out-of-corpus questions caught |
|---|---|---|
| dense cosine below 0.50 | 0 / 60 | 13 / 20 |
| best threshold on the rerank score | 4 / 60 | 15 / 20 |

Real questions bottom out at 0.5071 with a median of 0.6469, which is what leaves room
beneath 0.50. The cross-encoder score cannot be used this way. It ranks rather than
calibrates: it scored a bare plea for help at 0.8161 and the word "hello" at 0.7271, while
giving genuine questions as little as 0.0012.

Seven out-of-corpus questions still pass the gate. Two of them are in domain but too broad
for any single entry to answer, and those should ask the user for detail rather than be
refused at all, which the demo does not do.

## The evaluation set had to be repaired first

The template generates its test set from the corpus questions themselves, in four
variants: `verbatim` (unchanged), `natural` (a spoken-style prefix and suffix added),
`partial` (common words stripped) and `slang` (technical terms swapped for colloquial
ones). Measuring how much of the original wording each variant retains — using the same
tokenizer the system uses — gives 1.00, 1.00, 0.99 and 0.86 respectively. Only `verbatim`
and `natural` cover all 60 questions; `partial` applies to 27 and `slang` to 25, since
those two are generated only where the question contains something to strip or substitute.

Every configuration therefore scored a flat 1.0000 on all four. The set could not
distinguish a system that retrieves by meaning from one that merely matches words, and
no amount of improvement would have moved the numbers.

`partial` fails on Thai in particular: it strips words by splitting on spaces, but Thai
sentences barely contain any, so it removes almost nothing. On a corpus with more English
terms mixed in, that figure would be considerably lower.

The fix was to write 60 new questions by hand in `data/eval_paraphrases.txt`, avoiding the
original wording as far as possible. A corpus question such as *"ทำไมเน็ตมือถือช้าในบางที่ทั้งที่ขึ้นเต็มขีด"*
became *"สัญญาณขึ้นเต็มแต่โหลดอะไรก็ไม่ขึ้น เป็นเพราะอะไร"*. About 25% of the original tokens survive,
mostly function words that cannot be avoided. Every figure used for a decision in this
report comes from that variant alone.

## Results

All measurements use the same 60 questions in the `paraphrase` variant.

| Method | hit@1 | hit@10 | MRR | nDCG@3 | per query |
|---|---|---|---|---|---|
| dense only | 0.8500 | 0.9833 | 0.8961 | 0.8982 | 22.0 ms |
| BM25 only | 0.4000 | 0.6667 | 0.4953 | 0.4986 | 0.2 ms |
| hybrid with RRF | 0.6333 | 0.9500 | 0.7219 | 0.7109 | 20.0 ms |
| hybrid + rerank | 0.9333 | 0.9833 | 0.9482 | 0.9438 | 486.8 ms |

Across all variants, hybrid + rerank reaches hit@1 0.9828, hit@10 0.9957, MRR 0.9866 and
nDCG@3 0.9855.

Averages alone say little at this sample size, so the number of questions whose result
actually flips was counted alongside them.

| Comparison | left only | right only | net | McNemar |
|---|---|---|---|---|
| dense vs hybrid | 14 | 1 | −13 | p ≈ 0.0009 |
| hybrid vs hybrid + rerank | 0 | 18 | +18 | p < 0.001 |
| dense vs hybrid + rerank | 0 | 5 | +5 | p ≈ 0.063 |

The first two are statistically supported: fusing BM25 genuinely hurts on this corpus,
and cross-encoder reranking genuinely helps, most of all when the fusion has damaged the
ranking. The third does not reach significance, so the combined effect of both stages
should be read as a trend rather than a result.

### Why BM25 is weak here

Questions and answers share almost no rare exact tokens, because the text is Thai
explanatory prose throughout. This is the opposite of a corpus full of part numbers or
error codes, where BM25 has the advantage. Under the original RRF formula, which weights
both retrievers equally, BM25 drags the combined ranking down.

| dense : bm25 | rerank off | rerank on |
|---|---|---|
| 1 : 0 | 0.8961 | 0.9482 |
| 1 : 0.5 (used) | 0.7219 | 0.9482 |
| 1 : 1 (original) | 0.6967 | 0.9496 |
| 1 : 1.5 | 0.6165 | 0.7583 |
| 0 : 1 | 0.4953 | 0.7583 |

With reranking enabled, any weight between 0 and 1 produces identical results question by
question — zero differences, four wrong at rank one in every case. The reranker reorders
the whole candidate list anyway, so the weight only matters when reranking is off, which
is why it is set to 0.5 rather than 0. This value reflects the shape of the corpus, not a
universal setting; a corpus full of model numbers would invert it. It has to be measured
again whenever the corpus changes.

### The embedding model dominates everything else

| Model | dims | token limit | MRR | per query | corpus encode |
|---|---|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 128 | 0.5427 | 5.9 ms | 8 s |
| `intfloat/multilingual-e5-base` | 768 | 512 | 0.8387 | 8.5 ms | 9 s |
| `BAAI/bge-m3` | 1024 | 8192 | 0.8961 | 22.3 ms | 12 s |

Changing one model raised MRR from 0.5427 to 0.8961 while costing 16 additional
milliseconds per query, which is nothing next to the time the LLM spends writing an answer.

A related finding: `CHUNK_SIZE = 400` in the template is not an arbitrary number. A
400-character chunk of Thai text reaches at most 127 tokens, against MiniLM's limit of 128 —
exactly at the ceiling. The value is a property of the original model, not an optimum.

### Adding distractors barely moved the scores but sharpened the test

The corpus started at 172 pairs. A further 22 were added specifically to sit next to
existing entries: clearing a cache versus clearing app data, replacing a battery versus a
whole device versus a screen, an account password versus a Wi-Fi password, RAM full versus
storage full.

To make before and after comparable, `build_golden_set.py` was changed to select questions
that already have a hand-written paraphrase before filling the remainder at random. The
test set is therefore the same 60 questions in both runs, and the added documents act
purely as distractors — one variable changed, nothing else.

| | 172 documents | 194 documents |
|---|---|---|
| hybrid + rerank hit@1 | 0.9500 | 0.9333 |
| hybrid + rerank MRR | 0.9653 | 0.9482 |
| dense vs hybrid, questions differing | 10 : 1 | 14 : 1 |
| hybrid vs + rerank, questions differing | 0 : 15 | 0 : 18 |
| p value, dense vs hybrid | 0.012 | 0.0009 |

The headline scores hardly moved — hybrid + rerank went from 3 to 4 wrong — but the gap
between configurations widened and the p value improved by an order of magnitude. Reading
the averages alone would have concluded that the distractors achieved nothing. The useful
signal is the number of questions that flip between configurations. A test set can score
highly and still be useful for comparison, as long as enough questions change hands.

### Query preparation

Three modes were compared: raw questions, `normalize_query` with its substitution table
disabled, and the full version. All three produced hit@1 0.9333, hit@10 0.9833, MRR 0.9482
and nDCG@3 0.9438, to every digit, at roughly 0.5 seconds per question.

The substitution table has no measurable effect on this corpus, despite being written to
close exactly the gap it targets — mapping `wifi` to `ไวไฟ`, or the common misspelling
`อัพเดท` to `อัปเดต`. The reason is that bge-m3 already treats those as the same concept,
and the `slang` variant built to test this saturates at 1.0000 before anything is applied.
The table is kept because it costs nothing, but it must be recorded that it was measured
and found to do nothing here.

The three LLM-backed modes (`rewrite`, `multi_query`, `hyde`) still have no trustworthy
numbers, because the free Groq quota runs out mid-run. `QueryTransformer.transform()`
catches the failure and silently returns the original question, which is correct behaviour
in production but dangerous during evaluation: it yields plausible-looking numbers for a
stage that never executed. `eval_query_transform.py` now wraps the LLM to count calls and
failures and records `llm_calls`, `llm_failures` and `usable`. Rows where `usable` is false
must not be used.

### Answer quality

Measured with `llama-3.3-70b-versatile` on Groq over the first 20 test questions, with
hybrid + rerank enabled and conversation memory disabled so each question stands alone.
The correct document appeared among the three passed to the LLM in 0.95 of cases, every
answer carried an inline citation, none refused, and the average was 3.17 seconds per
question. Word overlap with the reference passages was 0.79, and with the reference answer
0.60.

Groq has since retired that model, and `config.LLM_MODEL` now names
`openai/gpt-oss-120b`. The numbers in this section were not measured again and still
describe the earlier model. Every retrieval number in this report is unaffected, because
`eval_retrieval` never calls an LLM.

Those last two need care. They are token-overlap ratios, not correctness judgements: an
answer rephrased in different words scores low while being entirely right. They indicate
whether an answer stays close to the source or drifts, and nothing more. The template
already contains a prompt for using an LLM as a judge in `prompt_templates.py`, but it is
not yet wired in — that is the obvious next step.

## What did not work

This section carries as much weight as the results. Each item is something that should
help by common sense, and did not.

**Removing Thai stopwords made retrieval 21% worse.** Leaving them in gives MRR 0.4953 at
an average of 95 tokens per document; removing them with the pythainlp list gives 0.3890 at
47 tokens. There are two reasons. BM25 already discounts frequent terms through IDF, so
removal adds nothing, while halving document length disturbs the length-normalisation term
across the whole corpus. And the list contains 1030 entries including *ทำไม*, *ยังไง* and
*ต่างกัน* — words that carry what the user is asking, not filler.

This is direct evidence against the premise that Thai underperforms because filtering is
inadequate. The problem is not filtering, and filtering harder makes it worse. The same
experiment on an unrelated corpus in an earlier iteration produced a 19% drop, so this is
not a quirk of one dataset.

**Normalisation alone changed nothing.** Measured step by step, the template's tokenizer
scores MRR 0.4834; adding text normalisation keeps it at 0.4834; adding hyphen joining
keeps it at 0.4834. Only the domain dictionary moved it, to 0.4953 — a single question,
gained because `พาวเวอร์แบงก์` had been split in two and `เอสเอสดี` in three. None of this
is statistically meaningful. It is kept because it guards against inconsistently encoded
input, which will appear as the corpus grows.

**Carrying conversation context into retrieval did not help.** Memory is on by default, but
testing showed it reaches only the answer prompt, never the search: `QueryTransformer` uses
history only when an LLM mode is enabled, and those are off by default. A follow-up such as
*"แล้วต้องเปลี่ยนตอนไหน"* is therefore searched with nothing indicating the subject.

An eight-case two-turn test set was built and two fixes were tried. The baseline finds the
right document at rank one in 5 of 8 cases and within the top three in 6 of 8. Prepending
the previous question raised the top-three figure to 7 but dropped rank one to 0, because
the previous question's own document took first place in every case, consuming one of the
three context slots with something the user had just been told. Adding it as an extra RRF
query changed nothing at all. Neither is an improvement, so both were reverted. The path
the template intends is enabling `rewrite` so the LLM makes the follow-up self-contained,
but the LLM modes remain unmeasured.

**Sentence-aware chunking cannot be measured here.** The corpus has 194 pairs producing
exactly 194 chunks, meaning no answer is long enough to be split. Changing the splitting
strategy cannot move any number, so it was not implemented, and the reason recorded instead.

## Changes to the template

`src/thai_text.py` is new. It centralises text preparation so that indexing and querying
always follow the same path.

| Problem | Before | After |
|---|---|---|
| transliterations shredded | `เอสเอสดี` → `['เอส','เอ','สดี']` | `['เอสเอสดี']` |
| | `พาวเวอร์แบงก์` → `['พาวเวอร์','แบงก์']` | `['พาวเวอร์แบงก์']` |
| identical text, different bytes | `เเปลก` ≠ `แปลก` | normalised before anything else |
| Thai numerals | `๓.๓` → `['๓','๓']` | `['3.3']` |
| hyphenated names | `Wi-Fi` → `['wi','fi']` | `['wifi','wi','fi']` |

Measurement showed `newmm` mis-segmenting 9 of 40 domain terms, which is why a domain
dictionary was added.

One caveat for anyone doing the same: `dict_trie()` replaces the main dictionary rather than
extending it. It must be given `set(thai_words()) | set(DOMAIN_WORDS)`, or the tokenizer
loses every other Thai word and performs worse than before.

Seven bugs in the template were found and fixed:

- `src/generator.py` — `NoLLM` split the prompt on the English marker `"reference data :"`
  while the prompt itself is Thai, so the no-LLM mode always answered "not found". The
  markers are now declared once in `prompt_templates.py` and shared.
- `src/generator.py` — the `no_context` flag was false whenever any chunk came back, but
  the retriever always returns top-k regardless of relevance, so callers were told the
  system had answered even when it had refused. It is now derived from the refusal message.
- `src/prompt_templates.py` — rule 2 told the model to answer "not found" when the context
  was insufficient, and rule 3 told it to always cite. It obeyed both and produced
  "not found [1] [2] [3]". The rules are now conditional on each other.
- `evaluation/eval_retrieval.py` — `all_misses = misses` overwrote the list each run, so
  only the last configuration was reported. It now accumulates per configuration.
- `evaluation/eval_retrieval.py` — the benchmark called the retriever directly, bypassing
  the query-preparation step that `main.py` always applies, and therefore reported lower
  figures than the system actually achieves.
- `main.py` — the block that prints the source list was commented out, so the
  `SHOW_SOURCES` switch in `config.py` had no effect. It is restored.
- `src/index_meta.py` — the corpus was compared by modification time, which git resets on
  checkout, so a fresh clone was warned that its index was stale on every run even though
  the file was byte-identical. It now compares a SHA-256 of the contents.

Also added: `groq` in `LLM_PROVIDERS` with a clear message when the key is missing;
`requirements.txt`, which the template lacked; the RRF weighting parameters in `config.py`,
which turned out to decide the outcome on this corpus; and
`evaluation/eval_query_transform.py`, since nothing previously measured that stage.

## Limitations

The system does not refuse. The measurement above records that none of the 20 answers
refused, which read as coverage at the time; it is more accurately the absence of a
refusal path, since the retriever hands over its top three whether or not they are
related. `serve.py` gates on distance to the corpus, but `main.py` still answers every
question from whatever comes back.

The test set has 60 questions. Only the two conclusions marked as significant should be
read as established; other differences should not be interpreted as meaningful. The best
configuration leaves just 4 of 60 wrong, so there is little headroom left to detect further
improvement — the finding that the substitution table does not help may reflect the absence
of room to help rather than the absence of value.

The corpus and the 60 rewritten questions come from the same author, who therefore knew
where the answers were. The figures should be read as an upper bound; a user who has never
seen the corpus would do worse. The rewritten questions also retain about 25% of the
original tokens, so this is not a fully disjoint-vocabulary test.

The test set is drawn from the same corpus being searched, so it measures only whether the
system finds what is there, not whether the corpus covers the questions people actually
ask. And the three LLM-backed query-preparation modes remain unmeasured for lack of quota.
