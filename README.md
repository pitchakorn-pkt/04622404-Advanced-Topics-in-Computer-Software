# 04622404 Advanced-Topics-in-Computer-Software

This repository contains lab exercises, source code, assignments, projects, and additional learning resources.

## Course Description 

**New academic study in computer software.**

The course follows the official course description and extends it with modern AI topics such as **LLM**, **RAG** and **Agentic AI**. It also includes hands-on labs, projects, and real-world applications. The complete list of topics is available in the **Course Contents** section.

## Owner Information
- 116730462035-0 Pitchakorn Phuadkhunthod
- Computer Engineering Department, Engineering Faculty, RMUTT

## Team Repository
- Please check out this repository for team project https://github.com/Automatic28m/Advance-AI-RAG

## Course Work

Each lab lives in its own folder, `LAB01` through `LAB10`, with the final project in `Final-Project/`.

| Lab | My part | Folder |
|---|---|---|
| LAB01 | Cleaning + Normalization (LLM data pipeline, stage 2), then a local embedding provider and a free answering model so the pipeline runs without a paid key — see the timeline in [`LAB01/README.md`](LAB01/README.md) | [`LAB01/`](LAB01/) |
| LAB02 | RAG retrieval system over a Thai food Q&A dataset, built step by step from loading to FAISS search — see [`LAB02/README.md`](LAB02/README.md) | [`LAB02/`](LAB02/) |
| LAB03 | no lab assigned — break in the course schedule | [`LAB03/`](LAB03/) |
| LAB04 | Full RAG system over a Thai Q&A corpus on everyday phone and computer problems, with hybrid retrieval, reranking, and a measured comparison of Thai-language retrieval settings — see [`LAB04/README.md`](LAB04/README.md) | [`LAB04/`](LAB04/) |
| LAB05 | Collected the problem write-ups from every system built in this course — 21 problems from `LAB01`, `LAB02` and `LAB04` in one folder, with the repetitions across them read side by side — see [`LAB05/README.md`](LAB05/README.md) | [`LAB05/`](LAB05/) |
| LAB06 | Team lead and module 08 (Docker / Integration) of ChuayDuay, an eight-person agentic RAG system for Thai phone and computer questions: the API contract, a running skeleton of all eight services, the Discord server and GitHub notifications, reviewing and merging every pull request, and the end-to-end tests — see [`LAB06/README.md`](LAB06/README.md); team repository [pitchakorn-pkt/chuayduay](https://github.com/pitchakorn-pkt/chuayduay) | [`LAB06/`](LAB06/) |
| LAB07 – LAB10 | not started yet | [`LAB07/`](LAB07/) … [`LAB10/`](LAB10/) |
| Final Project | not started yet | [`Final-Project/`](Final-Project/) |

Each finished lab has its own README covering the same four things: what was changed
from the lab template, how to run it, what came out of running it, and what the lab does
not establish. The last of those is the reason the reports differ in length — the
results section grows only where there are numbers to put in it.

A lab that is my own write-up also has a Thai version, `README.th.md`, linked from the
first line of each; the two carry the same content and the same figures. Each lab folder
installs from its own `requirements.txt` and is meant to be run from inside that folder.

`LAB01`, `LAB02` and `LAB04` each also carry a `problems/` folder: the problems found in
that system, one per stage of its pipeline, with the cause, how to check for it, and either
the fix applied or the reason none was. Each problem has a script that reproduces it from
the artefacts already committed — `cd LAB0x/problems && python main.py 0` runs them all.
Twenty-one problems in total, and most of them produce no error message at all.
`LAB05` gathers all three sets in one place and reads them across each other; `cd
LAB05/problems && python main.py 0` runs all twenty-one in one go.
