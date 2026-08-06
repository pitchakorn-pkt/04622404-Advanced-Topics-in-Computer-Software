# LAB02 — RAG Retrieval System (Thai Food Q&A)

English · [ภาษาไทย](README.th.md)

A retrieval pipeline built from scratch over a Thai-language knowledge base:
load a `.txt` source, chunk it, embed it, store the vectors in FAISS, and answer a
question by returning the closest stored passage. The knowledge base for this
submission is a Thai food guide covering 15 dishes.

This lab follows the DL-03 template. The pipeline code in `src/` and `labs/` is the
template's, unchanged apart from the file names and test queries it points at. What belongs to this
submission is the knowledge base (`data/thai_food_qa.txt`, written for this lab), the
test questions, and the run itself — building the index and checking what the system
actually retrieves. The observations below come from that run.

This is retrieval only. There is no generation step: the system returns the answer that
was stored, it does not write one.

## Structure

```text
LAB02/
│
├── data/
│   ├── thai_food_qa.txt                    # knowledge base, 90 Q&A pairs across 15 dishes
│   └── sample_questions.txt                # 10 questions used for manual checking
│
├── outputs/                                # produced by the labs, in order
│   ├── extracted_text.json                 # 90 Q&A records with line numbers
│   ├── chunks.json                         # 90 chunks with metadata
│   ├── embeddings.npy                      # (90, 384) float32
│   └── retrieval_results.json              # top-3 results for lab07's four queries
│
├── vector_db/
│   ├── document.index                      # FAISS IndexFlatIP
│   └── chunk_store.json                    # chunks and metadata, aligned to the index
│
├── labs/                                   # one step per file
│   ├── lab01_extract_text.py               # parse Q&A pairs out of the .txt
│   ├── lab02_chunking.py                   # split text into chunks
│   ├── lab03_create_embeddings.py          # encode the chunks
│   ├── lab04_create_vector_db.py           # build and save the FAISS index
│   ├── lab05_query_embedding.py            # encode a query
│   ├── lab06_similarity_search.py          # search the index
│   └── lab07_complete_retrieval.py         # the whole retrieval path end to end
│
├── src/                                    # the modules the labs call
│   ├── document_loader.py                  # reads the Q&A format
│   ├── text_splitter.py                    # chunking
│   ├── embedding_model.py                  # sentence-transformers wrapper
│   ├── vector_store.py                     # FAISS wrapper
│   └── retriever.py                        # encode query + search, in one call
│
├── config.py                               # paths and settings shared by every lab
├── requirements.txt
└── main.py                                 # interactive question loop
```

## The knowledge base

`data/thai_food_qa.txt` is 90 Q&A pairs: 15 dishes with 6 questions each. Five of the six
repeat for every dish — origin and region, main ingredients, characteristic taste, spice
level, and a cooking tip. The sixth varies: eleven dishes are asked how they are made,
three are asked how they differ from another dish (แกงเขียวหวาน vs มัสมั่น, ต้มข่าไก่ vs ต้มยำ,
ผัดไทย vs ผัดกะเพรา), and ลาบหมู is asked what it is seasoned with. The dishes are
ต้มยำกุ้ง, ผัดไทย, ส้มตำไทย, แกงเขียวหวานไก่, มัสมั่นเนื้อ,
ข้าวมันไก่, ผัดกะเพราหมูสับ, ต้มข่าไก่, ข้าวเหนียวมะม่วง, ลาบหมู, ข้าวซอย, แกงส้มชะอมกุ้ง,
หมูปิ้ง, ขนมครก and ยำวุ้นเส้น.

The format is a category header followed by pairs, separated by blank lines:

```text
[หมวด: ต้มยำกุ้ง]
Q: ต้มยำกุ้งใส่อะไรบ้าง วัตถุดิบหลักมีอะไร
A: วัตถุดิบหลักของต้มยำกุ้งได้แก่ กุ้งแม่น้ำหรือกุ้งทะเลตัวโต ตะไคร้ทุบ ...
```

The source is a text file, not a PDF, so `document_loader.py` records the line number of
each `Q:` and carries it through to the chunk metadata. That is what stands in for a page
number when a result needs to be traced back to the source.

## What the pipeline produced

| Step | Result |
|---|---|
| `lab01_extract_text.py` | 90 records parsed, each with category, question, answer and `line_no` |
| `lab02_chunking.py` | 90 chunks — one per pair. `CHUNK_SIZE` is 400 characters and the longest combined text is 314 (average 225), so the splitter never had to split anything |
| `lab03_create_embeddings.py` | `(90, 384)` float32, from `paraphrase-multilingual-MiniLM-L12-v2`, normalized at encode time |
| `lab04_create_vector_db.py` | FAISS `IndexFlatIP` over the 90 vectors. Because the vectors are normalized, inner product is cosine similarity |
| `lab05` / `lab06` | encode one query, search, print the top-k |
| `lab07_complete_retrieval.py` | four queries through `Retriever`, top-3 each, saved to `outputs/retrieval_results.json` |

A chunk is embedded as `Question: ... Answer: ...` — question and answer together, not the
answer alone. A question that resembles a stored question is therefore matched by the
question half, which is what makes a 90-vector index work at all.

## How to run

Python 3.12. The embedding model is downloaded on first use; nothing needs an API key.

```bash
cd LAB02
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python main.py                       # interactive; type exit, quit or q to leave
```

The index is committed, so `main.py` runs without rebuilding. If `data/thai_food_qa.txt`
changes, rebuild first:

```bash
python labs/lab01_extract_text.py
python labs/lab02_chunking.py
python labs/lab03_create_embeddings.py
python labs/lab04_create_vector_db.py
```

`config.py` resolves every path from its own location, so the folder can be moved without
editing anything.

## What it retrieves

The ten questions in `data/sample_questions.txt` were put through the retriever to see
where it holds up. Score is cosine similarity of the top result.

| Question | Top-1 score | Outcome |
|---|---|---|
| ต้มยำกุ้งใส่อะไรบ้าง | 0.8279 | correct |
| เมนูไหนไม่เผ็ดบ้าง | 0.7312 | wrong — returns "ผัดไทยเผ็ดไหม" |
| แกงเขียวหวานกับแกงมัสมั่นต่างกันยังไง | 0.7289 | correct |
| อาหารภาคอีสานมีเมนูอะไร | 0.6859 | wrong — returns ยำวุ้นเส้น, which the corpus calls nationwide; ลาบหมู is at rank 3 |
| ข้าวเหนียวมะม่วงทำยังไง | 0.7533 | correct |
| เมนูไหนเผ็ดที่สุด | 0.6594 | wrong — returns "ผัดไทยเผ็ดไหม" |
| ข้าวซอยเป็นอาหารภาคไหน | 0.7448 | wrong at rank 1, right at rank 2 |
| ผัดไทยกับผัดกะเพราใช้เส้นเหมือนกันไหม | 0.6855 | correct |
| เมนูที่ใช้กะทิมีอะไรบ้าง | 0.5559 | wrong — returns "ผัดไทยเผ็ดไหม" |
| ลาบหมูปรุงรสด้วยอะไร | 0.7826 | correct |

Five of the ten are answered correctly at rank 1, and every one of those five asks about a
single named dish.

They have something else in common, which limits what the result proves: all five already
exist in the corpus. Three are stored questions word for word (แกงเขียวหวานกับแกงมัสมั่น…,
ผัดไทยกับผัดกะเพรา…, ลาบหมูปรุงรสด้วยอะไร) and two are the opening words of a stored question
(ต้มยำกุ้งใส่อะไรบ้าง, ข้าวเหนียวมะม่วงทำยังไง). Every question that is phrased differently from
anything in the corpus is among the failures. This check therefore shows that near-exact
matching works; it says nothing about how the system handles a genuine paraphrase, because
none of the ten is one.

Two patterns account for the five that fail.

**Four of them ask across dishes** — which menu is not spicy, which dishes use coconut
milk, what Isan food is on the list. No stored pair answers those, because every vector is
one dish's answer to one question; nothing in the index aggregates over the corpus. The
retriever still returns its nearest neighbour, at 0.56–0.73, which is not far below the
scores of the questions it gets right. Nothing in the pipeline sets a floor, so a
question the corpus cannot answer looks the same as one it can.

**One is a ranking miss.** For ข้าวซอยเป็นอาหารภาคไหน the ingredients pair scores 0.7448 and
the pair that actually answers it — ข้าวซอยเป็นอาหารภาคไหน มีที่มาอย่างไร — scores 0.7113, so
it lands at rank 2. Both are about the right dish; the embedding does not separate "what
region" from "what ingredients" sharply enough. `main.py` prints only the top result, so
this one is shown as a miss rather than as a near miss.

## What was changed from the template

- `data/thai_food_qa.txt` replaces the template's dataset. The template ships 391 pairs
  in a different domain; this one is 90 pairs, 15 dishes, 6 questions each, written for
  this lab.
- `data/sample_questions.txt` was added for manual checking. No script reads it — it is
  input for `main.py` typed by hand, and the source of the table above.
- `config.py` points `SOURCE_FILE` at the new dataset; `main.py`'s banner and lab07's four
  test queries were rewritten to match the domain.
- Everything else in `src/`, `labs/` and `main.py` is the template's, including the
  settings: `CHUNK_SIZE` 400, `CHUNK_OVERLAP` 50, `TOP_K` 3, and
  `paraphrase-multilingual-MiniLM-L12-v2` as the embedding model.

## Limitations

- **No evaluation set, so no metrics.** The table above is ten hand-checked questions, not
  a measurement — and half of them repeat wording that is already in the corpus, so they
  cannot test paraphrasing. There is no golden set and no hit@k or MRR here; that work is
  in [`LAB04`](../LAB04/README.md), which does measure Thai retrieval properly.
- **One embedding model, untested against alternatives.** The template's default was kept.
  Whether it is a good choice for Thai is not established by anything in this folder.
- **Chunking is untested at this scale.** No answer exceeds 400 characters, so
  `text_splitter.py` returned every text unchanged. The chunking step runs but never does
  anything, and a longer corpus would exercise a code path this lab never tried.
- **`main.py` shows the top result only.** `config.TOP_K` is 3, but the call passes
  `top_k=1`; both that and the commented-out lines around it come from the template.
  There is also no score threshold, so the system always answers, however far off it is.
- **Retrieval only.** Answers are returned verbatim from the corpus. Nothing rephrases an
  answer or combines two of them, which is why the cross-dish questions have no path to a
  correct answer.
