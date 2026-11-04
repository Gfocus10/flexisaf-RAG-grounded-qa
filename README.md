# Grounded Q&A over Nigerian University Documents (RAG)

A retrieval-augmented question answering assistant built for the Flexisaf AI engineer internship (RAG module). It answers questions about 10 public Nigerian university and JAMB documents, cites the source file and PDF page for every factual answer, and replies "Not enough information in the provided sources." when the documents do not contain the answer.

## How it works

1. Extract text from each PDF page, keeping the page number.
2. Split each page into chunks of up to 800 characters with 150 characters of overlap. Chunks never cross a page boundary, so every citation points to one exact page.
3. Embed the chunks with all-MiniLM-L6-v2 (local, no API) and store them in a Chroma collection.
4. For a question, detect any university named in it, filter the search to that university's files, and retrieve the top passages.
5. Send the passages and the question to Gemini with strict rules: answer only from the sources, cite the source tags, refuse when the answer is missing, and correct false assumptions.
6. Show the answer with a Sources list built by code from the retrieved pages, never from text the model wrote.

## Repository layout

```
README.md
requirements.txt
.env.example
data/
  raw/                       original PDFs, unchanged
  document_register.csv      source register (title, institution, URL, date accessed, permission note)
  extracted/pages.jsonl      page text produced by extract_pages.py
  chunks/chunks_800_150.jsonl
  eval_questions.json        20 evaluation questions with expected answers and sources
  answer_checks.json         key-fact patterns used by the automatic answer checks
src/
  extract_pages.py           PDF to page text
  chunk_pages.py             page text to chunks
  build_index.py             embeddings and Chroma index
  retrieve.py                search with institution filter
  llm.py                     Gemini calls with retry and fallback model
  rag.py                     grounded answer pipeline (command line app)
  eval_retrieval.py          retrieval evaluation
  eval_answers.py            answer evaluation
docs/
  evaluation.md              results, top-k comparison, failure examples
  change_log.md              setting and prompt change log
  risks_and_limitations.md
evidence/                    CSV and JSON output of every evaluation run
```

The `chroma_db/` folder is not committed. Rebuild it with the steps below.

## Setup (Windows, Git Bash, Python 3.13)

```
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your own Gemini API key. Never commit `.env`.

```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_FALLBACK_MODEL=gemini-3.6-flash
```

Check the connection:

```
python src/llm.py
```

## Build the index

```
python src/extract_pages.py
python src/chunk_pages.py
python src/build_index.py
```

Expected: 1,052 pages with text, 2,555 chunks, and a Chroma collection named `uni_docs_800_150`.

## Ask a question

```
python src/rag.py "Can students cook in their hostel rooms at Nnamdi Azikiwe University?"
```

Example output:

```
Answer: Cooking in rooms is prohibited except in designated areas (where available) [S1, S4].

Sources:
  [S1, S4] Hostel Rules Policies and Guidelines (unizik_hostel_rules.pdf), PDF page 2
```

When the documents do not contain the answer:

```
Answer: Not enough information in the provided sources.

Sources: none (the system declined to answer)
```

Page numbers are PDF positions (the page counter in a PDF viewer), not the numbers printed on the page. Options: `--k` (default 6), `--no-filter` (turn off the university filter).

## Evaluate

```
python src/eval_retrieval.py --k 6
python src/eval_answers.py --k 6 --label final
```

The answer evaluation waits 4 seconds between questions to stay within the free-tier rate limit and takes about 2 minutes. Results are written to `evidence/`.

## Results at a glance

On the 20 evaluation questions (10 answerable, 3 ambiguous, 4 unanswerable, 3 misleading):

1. Retrieval found an expected page in the top 6 for 16 of 16 questions that have expected sources.
2. The final answer run (k=6) passed 20 of 20 automatic checks, and all 4 unanswerable questions were refused.
3. These numbers are on the same questions used to find and fix problems, from single runs, so they are optimistic. See `docs/evaluation.md` and `docs/risks_and_limitations.md`.

## Documents used

Ten public documents from ABU, BUK, UNILORIN, UNIZIK, UDUS, NOUN and JAMB, listed with source URLs, access dates and permission notes in `data/document_register.csv`. The originals are not modified. No explicit reuse licence was found for them, so they are included only as sample documents for this assignment.