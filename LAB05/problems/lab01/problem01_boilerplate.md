# Problem 01 — The boilerplate rule removes real requirements

English · [ภาษาไทย](problem01_boilerplate.th.md) · reproduce: `python main.py 1`

## The rule

`collect_boilerplate()` drops any line that appears in five or more documents,
counting documents rather than occurrences, on the reasoning that a line
repeated across unrelated postings is a company blurb or an equal-opportunity
statement rather than part of the job. Lines of four words or fewer are kept —
they are section headings, and the chunking stage uses them as boundaries
(`cleaning.py:73-91`).

Re-running it over the committed Collection output reproduces
`outputs/boilerplate_lines.json` exactly: 77 lines, every one identical.

## Where the reasoning breaks

The rule is sound only if the postings are independent of each other. In this
corpus they are not:

| employer | postings |
|---|---|
| Canonical Ltd. | 36 |
| Nebius | 9 |
| Experian | 7 |
| iHerb | 5 |
| 58 employers | 1 each |

One employer accounts for 36 of the 160 Jobicy postings. Its postings repeat
each other by nature, so its lines cross a five-document threshold without being
boilerplate at all.

## What it costs, by employer

Share of text surviving the boilerplate rule specifically — HTML stripping and
whitespace normalisation excluded, so this isolates the rule under discussion:

| employer | postings | text kept |
|---|---|---|
| Canonical Ltd. | 36 | 67% |
| Nebius | 9 | 63% |
| Experian | 7 | 95% |
| iHerb | 5 | 41% |
| Welo Global | 5 | 100% |
| the 58 single-posting employers | 1 each | **100%** |

An employer who posted once loses nothing at all. iHerb, with five postings,
keeps 41%. The rule penalises an employer in proportion to how many jobs they
advertise, which has nothing to do with whether the text is filler.

> The README for this lab reports 86% / 86% / 59% / 34% for the same employers.
> Those figures are measured against the raw length *including HTML markup*, so
> the ~14% that HTML stripping removes is counted as loss for everyone. Both are
> correct; this page isolates the rule, the README reports total shrinkage.

## Lines that are not blurbs

Three of the 77 collected lines:

```
Experience with Linux (Debian or Ubuntu preferred)
Experience with Microsoft Office Suite (Word, Excel, PowerPoint)
Bachelor's Degree in Computer Science or related field preferred
```

These are requirements, removed from every posting that listed them. That
reaches the example query in the lab README directly: a search for who hires for
Kubernetes work is answered from postings whose stated Linux requirement is no
longer in the text.

## How to check

1. Run `python main.py 1` and read the "text kept" column. A wide spread across
   employers means the rule is penalising posting volume, not content.
2. Read `outputs/boilerplate_lines.json` by eye — all 77 lines. That file is
   written on every cleaning run for exactly this purpose.

## What would fix it

Count the number of **employers** a line appears under, rather than the number
of documents. A blurb repeated by many companies still gets dropped; a
requirement repeated by one company inside its own postings survives.

This has not been changed. The cleaned output is what every later stage was
built and measured against, so changing the rule means re-running the whole
chain.
