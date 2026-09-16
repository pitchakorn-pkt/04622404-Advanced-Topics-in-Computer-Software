# Problem 02 — Two schemas, and a field the rule empties

English · [ภาษาไทย](problem02_schemas.th.md) · reproduce: `python main.py 2`

## Two schemas in one corpus

| source | records | id type | text fields |
|---|---|---|---|
| aidevboard_ai | 20 | `str` — `'48720738-0f4b-483d-…'` | `description` |
| jobicy_cyber_security | 28 | `int` — `149591` | `jobDescription`, `jobExcerpt` |
| jobicy_devops_infra | 32 | `int` | `jobDescription`, `jobExcerpt` |
| jobicy_software_en | 100 | `int` | `jobDescription`, `jobExcerpt` |

Jobicy uses camelCase with integer ids; AIDevBoard uses snake_case with UUID
strings. Both key on `id`.

This is only visible by opening the data. Code written from the spec sees one
schema, and the other source passes through cleaning untouched with no error at
all — `process_records()` only rewrites fields that are actually present
(`cleaning.py:130-131`), so a record whose field names do not match is copied
through whole.

The finding was sent to the team as a comment on the pull request rather than
handled silently, because the chunking stage downstream keys on the same field
names.

## The field the rule empties

`jobExcerpt` is the opening of `jobDescription`, which is usually the company
blurb. Counting it as its own document makes the same text count twice per
posting, so it crosses the five-document threshold more easily and then gets
removed:

| | boilerplate lines | excerpts emptied |
|---|---|---|
| counting `jobExcerpt` as a document | 80 | **30 of 160** |
| not counting it (what runs) | 77 | 0 of 160 |

Two separate exclusions are needed and both are in place:

1. `jobExcerpt` is exempt from **removal** — `KEEP_BOILERPLATE_FIELDS`
   (`cleaning.py:31`)
2. `jobExcerpt` is left out of the **count** — `02_data_cleaning.py:50-56`

Doing only the first leaves the field intact but lets its text push
`jobDescription` lines over the threshold faster than they should go. The two
rows above are exactly that difference.

## The other exemption, and why

Lines of four words or fewer are never dropped, however often they repeat
(`cleaning.py:36`). They are headings — `Requirements`, `The Role` — and the
chunking stage uses them as split boundaries. Every chunk in this corpus was
produced with `strategy: heading`.

Drop the headings and the next stage immediately splits in the wrong places.
It is a small example of how tightly one stage's decision binds the next.

## How to check

Count `Q`-style structural markers before and after every stage, and diff the
field names present in each source file before writing code against them. The
run is verified structurally already: `02_data_cleaning.py:30-39` asserts that
no record lost its `id`, gained or lost a key, or changed any non-text value.
