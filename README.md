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
