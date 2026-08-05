"""Ask the pipeline a question.

    python main.py                                   # interactive
    python main.py -q "who is hiring for Kubernetes work?"
    python main.py -q "senior AI roles" --source aidevboard_ai --top-k 8
    python main.py -q "remote security jobs" --category Cybersecurity
    python main.py --build                           # build the index first
    python main.py -q "kubernetes" --no-llm          # retrieval only, no model

This is the front door to what the pipeline produced: the job postings have
been collected, cleaned, chunked, annotated and embedded, and this asks
questions of the result. Every answer is built only from passages retrieved out
of the vector store, and every claim in it carries the posting it came from.

--no-llm stops one step short of that, printing the passages the search found
and what they scored. It is how the retrieval is judged on its own, and the
only way to run this at all when no LLM is reachable.

The store lives in Pipeline/chroma_db and is not committed, so a fresh checkout
has to build it once with --build. That needs Pipeline/outputs/embeddings_*.json,
which is not committed either -- see the pipeline README for the two commands
that produce it.
"""

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent / "Pipeline"))

from vector_store import (  # noqa: E402  (the path above has to be set first)
    DEFAULT_COLLECTION,
    DEFAULT_LLM_MODEL,
    DEFAULT_TOP_K,
    PERSIST_DIR,
    answer,
    citation_of,
    create_collection,
    embedding_provider,
    embedding_settings,
    get_client,
    load_dotenv,
    load_records,
    open_store,
    search,
    upsert,
)

FILTER_FIELDS = ("source", "level", "category", "location", "author")
PREVIEW = 200


def build_store(persist_dir=PERSIST_DIR, collection_name=DEFAULT_COLLECTION):
    """Index the Embedding stage output, replacing whatever was there before."""
    records = load_records()
    model, dimension = embedding_settings(records)
    provider = embedding_provider(records)
    print(f"indexing {len(records)} vectors ({provider}/{model}, dimension {dimension})")

    collection = create_collection(
        get_client(persist_dir), name=collection_name,
        dimension=dimension, model=model, provider=provider, reset=True,
    )
    count = upsert(collection, records)
    print(f"indexed {count} points into {persist_dir}\n")
    return collection


def collect_filters(args):
    """Turn the --source/--level/... options into a filter dict."""
    return {
        field: getattr(args, field)
        for field in FILTER_FIELDS
        if getattr(args, field) is not None
    }


def preview(text):
    """One-line, truncated view of a passage so it fits on screen."""
    flat = " ".join(text.split())
    return flat[:PREVIEW] + ("..." if len(flat) > PREVIEW else "")


def retrieve_only(collection, query, top_k, filters):
    """Print what the search returns, without asking a model to write anything.

    This is the whole pipeline up to the last step: the passages, what they
    came from, and how close each one was. Useful on its own for judging the
    retrieval, and the only way to exercise it when no LLM is reachable.
    """
    hits = search(collection, query, top_k=top_k, filters=filters or None)
    print()
    for position, hit in enumerate(hits, start=1):
        meta = hit["metadata"]
        print(f"[{position}] {hit['score']:.3f}  {citation_of(hit)}")
        print(f"    {meta['doc_title']} - {meta['author']} ({meta['location']})")
        print(f"    {preview(hit['text'])}\n")

    if not hits:
        print("  (nothing matched -- check the filters)\n")


def ask(collection, query, top_k, filters, model):
    """Answer one question and print it with the postings behind it."""
    result = answer(query, collection, top_k=top_k, filters=filters or None,
                    model=model, log=lambda *values: None)

    print(f"\n{result['answer']}\n")
    print("sources:")
    for source, ident, index in result["citations"]:
        hit = next(h for h in result["hits"] if h["chunk_id"] == f"{source}:{ident}:{index}")
        meta = hit["metadata"]
        print(f"  [{source}:{ident}#{index}]  {meta['doc_title']} - {meta['author']} "
              f"({meta['location']})")

    # A tag the model made up points at a posting that was never retrieved, so
    # the claim attached to it is not grounded in anything.
    if result["invented"]:
        print("\nwarning: the answer cites passages it was never given:")
        for source, ident, index in result["invented"]:
            print(f"  [{source}:{ident}#{index}]")

    if not result["citations"]:
        print("  (none -- the answer is not grounded in any retrieved posting)")


def interactive(collection, top_k, filters, model, use_llm=True):
    """Keep asking until the reader is done."""
    print("Ask a question, or press Enter on an empty line to quit.")
    if not use_llm:
        print("--no-llm: retrieval only, nothing will be written for you.")
    if filters:
        print(f"filters: {filters}")
    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not query:
            return
        if use_llm:
            ask(collection, query, top_k, filters, model)
        else:
            retrieve_only(collection, query, top_k, filters)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-q", "--query", default=None,
                        help="ask one question and exit; omit for interactive mode")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                        help="how many passages to retrieve")
    parser.add_argument("--build", action="store_true",
                        help="rebuild the index from Pipeline/outputs/embeddings_*.json")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--persist-dir", default=str(PERSIST_DIR))
    parser.add_argument("--model", default=DEFAULT_LLM_MODEL, help="the model that answers")
    parser.add_argument("--no-llm", dest="use_llm", action="store_false",
                        help="retrieve and print the passages, without writing an answer")
    for field in FILTER_FIELDS:
        parser.add_argument(f"--{field}", default=None, help=f"only postings whose {field} matches")
    return parser.parse_args()


def main():
    # Job text carries curly quotes and dashes, which the Windows console
    # encoding cannot represent.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    load_dotenv()

    if args.build:
        collection = build_store(args.persist_dir, args.collection)
    else:
        try:
            collection = open_store(args.persist_dir, args.collection)
        except Exception as error:
            print(f"could not open the vector store: {error}")
            print("run 'python main.py --build' once to create it.")
            return 1

    filters = collect_filters(args)
    if args.query and args.use_llm:
        ask(collection, args.query, args.top_k, filters, args.model)
    elif args.query:
        retrieve_only(collection, args.query, args.top_k, filters)
    else:
        interactive(collection, args.top_k, filters, args.model, args.use_llm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
