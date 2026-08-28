# LAB04 — Problems in this RAG system, and what was done about them

English · [ภาษาไทย](README.th.md)

Nine problems found in the retrieval-augmented Q&A system in [`../`](../),
one per stage of the pipeline it runs. Each is written up with what happens,
why, how to check for it, and either the fix that was applied or the reason none
was.

Every number here was measured on this system. Each problem has a script that
reproduces it from the artefacts this repository already commits — the chunk
store, the FAISS vectors, the BM25 index and the evaluation outputs. Nothing
downloads a model and nothing needs an API key.

## Running it

```bash
cd LAB04/problems
python main.py        # menu
python main.py 4      # one problem
python main.py 0      # all nine, about half a second
```

Dependencies are LAB04's own (`../requirements.txt`); no new ones were added.

## The nine

| # | Problem | What the system actually does | Status |
|---|---|---|---|
| [1](problem01_hallucination.md) | Hallucination | never refuses — refusal rate 0.0000 over 20 questions | gated at `RELEVANCE_MIN = 0.50`, 0/60 false rejections |
| [2](problem02_vocabulary.md) | Vocabulary mismatch | `otp` and `โอทีพี` are unrelated tokens; 13 of 50 loanwords mis-segmented | `SLANG_MAP` + a merged tokeniser dictionary |
| [3](problem03_data_quality.md) | Data quality | parser drops malformed entries silently; a corpus can be false and still score full marks | domain replaced after 5 of ~15 facts proved wrong |
| [4](problem04_chunking.md) | Chunking | has never run — 194 records in, 194 chunks out, longest 392 of 400 | documented, deliberately unchanged |
| [5](problem05_metadata.md) | Metadata | `category` on all 194 chunks, read by zero files on the retrieval path | open — two options, both costed |
| [6](problem06_reranking.md) | Re-ranking | hit@1 0.6333 → 0.9333 while hit@10 barely moves | reranking on; 20 ms → 490 ms |
| [7](problem07_generation.md) | Faithfulness | 95% correct retrieval, 0.5957 correctness; one answer contradicted its own citation | 3 prompt/flag bugs fixed; `JUDGE_PROMPT` still unwired |
| [8](problem08_config.md) | Configuration | fusion weight is corpus-specific; a withdrawn model degrades silently | measured table in `config.py`; index check now hashes content |
| [9](problem09_evaluation.md) | Evaluation | 4 of 5 question variants sit at 1.0000 and separate nothing | `paraphrase` used throughout; `usable` flag added |

## What connects them

Six of the nine are failures that produce no error message. The chunking stage
does nothing, the category field is never read, the query transformer swallows
every exception, a withdrawn model falls back to raw corpus text, the citation
list is built and discarded, and four fifths of the test set cannot tell two
configurations apart. In each case the system kept running and the numbers kept
looking reasonable.

That is the pattern worth carrying forward: in a RAG pipeline the dangerous
failures are the quiet ones, because every stage has a sensible fallback and the
output always looks like an answer.

## Where each one comes from

Problems 1, 6, 7, 8 and 9 are specific to the full pipeline in this lab.
Problem 4 appears in [`../../LAB02`](../../LAB02) in a stronger form, and
problem 3 has its counterpart in the cleaning stage of
[`../../LAB01`](../../LAB01). Each of those labs documents its own set.
