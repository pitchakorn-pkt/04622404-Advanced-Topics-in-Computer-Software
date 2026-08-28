# Problem 02 — The words typed are not the words stored

English · [ภาษาไทย](problem02_vocabulary.th.md) · reproduce: `python main.py 2`

## What happens

Three separate failures share one cause: the keyword half of retrieval matches
tokens, and Thai gives it several ways to see two spellings of one word as
unrelated.

**Cross-script.** The user types the English word, the corpus stores the Thai
transliteration. Run against the real BM25 index, the top hit is a different
document before and after normalisation:

| typed | BM25 top-1 | after `normalize_query()` | BM25 top-1 |
|---|---|---|---|
| `otp ไม่มา` | 4.32 มีคนโทรมาอ้างว่าเป็นเจ้าหน้าที่ | `โอทีพี ไม่มา` | 9.08 รหัสโอทีพีบอกใครได้บ้าง |
| `cloud เต็ม` | 4.20 แรมเต็มกับพื้นที่เก็บข้อมูลเต็ม | `คลาวด์ เต็ม` | 7.07 คลาวด์เต็มแต่ไม่อยากเสียเงินเพิ่ม |
| `ทำ backup` | 2.22 ทำมือถือหายแล้วมีแอปยืนยันตัวตน | `ทำ สำรองข้อมูล` | 7.69 สำรองข้อมูลมือถือทำยังไงให้ครบ |
| `bluetooth ไม่ติด` | 5.25 หน้าจอสัมผัสไม่ค่อยติด | `บลูทูธ ไม่ติด` | 8.28 ปิดไวไฟกับบลูทูธช่วยประหยัดแบต |

Every one of the four returns a different document. Misspellings behave the same
way, more mildly: `อัพเดทแล้วช้า` finds the right document at 5.60, and
`อัปเดตแล้วช้า` finds the same one at 9.14.

**Tokenisation.** Thai is written without spaces, so BM25 needs a tokeniser
before it can index anything. pythainlp's `newmm` does not know the loanwords
this domain runs on, and shreds them into fragments that are not words:

| word | standard dictionary | with `DOMAIN_WORDS` |
|---|---|---|
| แอป | `['แอ', 'ป']` | `['แอป']` |
| เอสเอสดี | `['เอส', 'เอ', 'สดี']` | `['เอสเอสดี']` |
| พาวเวอร์แบงก์ | `['พาวเวอร์', 'แบงก์']` | `['พาวเวอร์แบงก์']` |
| อะแดปเตอร์ | `['อะ', 'แด', 'ปเตอร์']` | `['อะแดปเตอร์']` |

13 of the 50 entries in `DOMAIN_WORDS` are affected. A fragment like `สดี` can
never match anything on the corpus side, so the query silently loses the term
that mattered most.

**Paraphrase.** Keyword matching does not survive rewording at all:

| variant | BM25 MRR | hit@1 |
|---|---|---|
| verbatim | 1.0000 | 1.0000 |
| slang | 1.0000 | 1.0000 |
| partial | 1.0000 | 1.0000 |
| natural | 1.0000 | 1.0000 |
| paraphrase | 0.4953 | 0.4000 |

Dense retrieval scores 0.8961 on that same paraphrase set — near enough to
double.

## Why

`tokenize()` (`thai_text.py:84`) is the single point where both the corpus and
the query are turned into tokens. Anything it does inconsistently between the
two sides turns matching words into non-matching ones. The three failures above
are three ways that consistency can hold while still being wrong: both sides
agree that `otp` and `โอทีพี` are different tokens, both sides agree that
`เอสเอสดี` is three fragments, and both sides agree on tokens while the user's
sentence shares almost none of them.

## How to check

`python main.py 2` runs all three against the committed indexes. For a new
corpus:

- feed the domain's loanwords through `word_tokenize` twice, once with and once
  without the custom dictionary, and read the difference
- compare a keyword-only run on verbatim questions against one on hand-rewritten
  questions; a large gap means the retriever is matching strings, not meaning

## What was done

`SLANG_MAP` (`query_transform.py:48-69`) rewrites the query before retrieval.
It uses no model, costs nothing, and runs on every query through
`normalize_query()`, which is why it is on by default while the LLM-based
transforms are not.

`DOMAIN_WORDS` (`thai_text.py:33-44`) is merged into the tokeniser's
dictionary. The merge matters: `dict_trie()` **replaces** the main dictionary
rather than extending it, so passing only the domain words leaves newmm unable
to segment ordinary Thai. The call has to be
`dict_trie(dict_source=set(thai_words()) | set(DOMAIN_WORDS))`
(`thai_text.py:49`).

Thai stopword removal was tried and reverted. It made retrieval worse:

| | MRR | mean tokens per document |
|---|---|---|
| stopwords removed | 0.4970 | 50 |
| stopwords kept | 0.6136 | 90 |

BM25 already discounts common terms through IDF, so removing them adds nothing,
while halving document length distorts the length-normalisation term across the
whole corpus. pythainlp's 1030-word list also contains `ทำไม`, `ยังไง` and
`ต่างกัน` — the words that carry what the user is actually asking.

## Note on the file header

`thai_text.py:17-21` still illustrates the tokenisation problem with
`ออสซิลโลสโคป` and `ไมโครคอนโทรลเลอร์`, and quotes a figure of 15 of 43 words.
Those come from the IoT corpus this lab used before the domain change; neither
word is in the current `DOMAIN_WORDS` and neither appears in the corpus. The
figure for the current corpus is 13 of 50, printed by the script.
