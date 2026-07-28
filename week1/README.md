# Week 1 — LLM Data Pipeline

**My part: Cleaning + Normalization** (stage 2)

| File | |
|---|---|
| `Pipeline/cleaning.py` | `clean()` strips HTML, boilerplate and repeated lines; `normalize()` applies Unicode NFC, Thai digit and tone-mark folding, and whitespace cleanup |
| `Pipeline/02_data_cleaning.py` | runs the stage over every Collection output and prints a before/after sample |
| `Pipeline/outputs/cleaned_*.json` | result, 180 records |
| `Pipeline/outputs/boilerplate_lines.json` | the boilerplate the run detected |

**From the team, used as input:** Collection (stage 1) — `Pipeline/01_data_collection.ipynb` and `Pipeline/outputs/extracted_text_*.json`.

Pulled with `git subtree` from [Automatic28m/Advance-AI-RAG](https://github.com/Automatic28m/Advance-AI-RAG), branch `feature-pitchakorn-pkt`.

---

# Advance Topics in Computer Software course
## Computer Engineering - RMUTT
## The purpose is to study the 8 steps of LLM data pipeline since Data Collection until the LLM / Retrieval to finally learn the methodology of RAG or Retrieval-Augmented Generation.
## Team members
- 116730462006-1 Phanlop Boonluea
- 116730462011-1 Saran Tanyavikai
- 116730462016-0 Sakda Baokam
- 116730462032-7 Praphavit Kaorak
- 116730462033-5 Praphakorn Pitamma
- 116730462035-0 Pichakorn Puangkunthod
