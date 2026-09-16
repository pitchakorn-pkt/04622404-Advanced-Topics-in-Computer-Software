# Problem 05 — Remote calls that fail without saying why

English · [ภาษาไทย](problem05_http.th.md) · reproduce: `python main.py 5`

The pipeline speaks HTTP through `urllib` alone, adding no dependency. That is a
deliberate choice and it cost three things. Two are fixed in the code as it
stands; one is not.

## 1. Cloudflare rejects urllib's User-Agent — fixed

`urllib` announces itself as `Python-urllib/3.x`, which Cloudflare rejects
outright on some endpoints: HTTP 403 carrying `error code: 1010`, before the
request ever reaches the API.

What made it hard to find: 403 reads as "this key is not allowed", which is the
first thing anyone checks — and it has nothing to do with the key. Groq answers
403 rather than 404 here, which makes it look even more like a permissions
problem.

```
embedding.py:77    USER_AGENT = "Advance-AI-RAG/1.0"
embedding.py:409   headers = {"User-Agent": USER_AGENT, **headers}
```

Naming the caller is enough to pass, and is what any HTTP client would have sent
anyway.

## 2. The retry discarded the response body — fixed

`post_with_retry()` caught `HTTPError` and reported the status code alone. Every
failure looked identical from outside, and the text that said what was actually
wrong — `error code: 1010` above — was thrown away with it.

```
embedding.py:435   detail = error.read().decode("utf-8", "replace").strip()[:400]
embedding.py:84    RETRY_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504})
```

429 is retriable because the Gemini free tier meters tokens per minute and
answers 429 for a whole batch once that window is full — a temporary failure
that waiting resolves. 403 is not in the set: waiting does not help.

Fixing this is what made 1 and 3 findable quickly.

## 3. A model name the provider withdrew — not fixed

```
vector_store.py:84   DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"
```

Groq removed that model on 18 August 2026 — found while working on LAB04, which
uses the same provider and where the config was updated.

The symptom is a request rejected for the model name rather than the key or the
quota, which a status code alone cannot distinguish. Fix 2 is what makes it
distinguishable.

The code already warns about this at `vector_store.py:74-76`, saying to check
the model list before changing it. But that list changes on its own, without the
code knowing. A constant that points at something outside the system can always
go stale.

## The shared lesson

A network failure arrives as a three-digit number, which says far too little to
diagnose. What says something is the body that comes with it. Throwing that body
away is always more expensive than it looks.
