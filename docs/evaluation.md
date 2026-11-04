# Evaluation

## Evaluation set

20 questions in `data/eval_questions.json`: 10 answerable, 3 ambiguous (no university named, different universities give different rules), 4 unanswerable (3 in-domain with no amount stated in the documents, 1 out of scope), and 3 misleading (false premise). Each question has an expected answer containing only facts from the PDFs, and expected source files and PDF pages. The author checked the expected answers against the PDFs. Page numbers are PDF positions, not printed page numbers.

## Retrieval results

A question passes if at least one expected (file, PDF page) pair is among the top k results. Sixteen questions have expected sources (the 4 unanswerable ones have none).

| Setting | Answerable | Ambiguous | Misleading | Total |
|---|---|---|---|---|
| No university filter, k=4 | 8/10 | 3/3 | 1/3 | 12/16 |
| University filter, k=2 | 9/10 | 3/3 | 2/3 | 14/16 |
| University filter, k=4 | 10/10 | 3/3 | 3/3 | 16/16 |
| University filter, k=6 | 10/10 | 3/3 | 3/3 | 16/16 |

Top-k comparison: k=2 loses q09 and q19, whose answer pages rank 4th and 3rd at k=4. k=4 and k=6 both find an expected page for every question, but only k=6 finds all three expected sources for the multi-university question q13 (2 of 3 at k=4). A larger k sends more text to the model for each question.

Files: `evidence/retrieval_eval_800_150_k4.csv` (no filter), `..._k2_filter.csv`, `..._k4_filter.csv`, `..._k6_filter.csv`. The earlier file `evidence/v1_before_ground_truth_fix.csv` was produced before the expected sources of q11 to q13 were corrected.

## Answer results

Automatic checks per question: the refusal is correct (unanswerable must be refused, the others must not), the answer contains the key facts, the cited pages include an expected page, and no invented source tag appears. The author also read the answers.

| Run | Setting | Answerable | Ambiguous | Misleading | Unanswerable | Total |
|---|---|---|---|---|---|---|
| First run (strict checks) | k=4, v1 prompt | 9/10 | 1/3 | 2/3 | 4/4 | 16/20 |
| v1 baseline (corrected checks) | k=4, v1 prompt | 10/10 | 1/3 | 2/3 | 4/4 | 17/20 |
| v2 prompt | k=4 | 10/10 | 2/3 | 2/3 | 4/4 | 18/20 |
| v2 prompt | k=6 | 10/10 | 3/3 | 3/3 | 4/4 | 20/20 |

Questions that failed in any run:

| Question | First run | v1 baseline | v2, k=4 | v2, k=6 | Cause |
|---|---|---|---|---|---|
| q10 | FAIL | PASS | PASS | PASS | Check too strict: it demanded the international fee although the question asks only for the local one |
| q11 | PASS | FAIL | PASS | PASS | Baseline answer had no citation tags (model did not follow the citation rule in that run) |
| q12 | FAIL | PASS | PASS | PASS | Expected answer was incomplete: BUK's general 75% rule (PDF page 17) was missing |
| q13 | FAIL | FAIL | FAIL | PASS | UNIZIK page not retrieved at k=4, so the answer listed 2 of 3 universities |
| q20 | FAIL | FAIL | FAIL | PASS | Model refused although the evidence was retrieved (see below) |

Files: `evidence/answer_eval_first_run_strict_checks.csv`, `answer_eval_800_150_k4_filter_v1_baseline.csv`, `answer_eval_800_150_k4_filter_v2_prompt.csv`, `answer_eval_800_150_k6_filter_v2_prompt.csv` (each also has a JSON with the full retrieved passages).

## Retrieval failure example

Question q10: "How much does Ahmadu Bello University charge for collecting a local academic transcript?" Without the university filter the top 4 results were ABU handbook pages 40, 44, 46 and 44, which are introduction and history pages that repeat the university name. The page with the answer (PDF page 111, "Payment of N10,000 for local and N45,000 for international transcript") was not retrieved. The same pattern caused q18 (the ABU title page, only 85 characters, and the preamble ranked first) and q09 (the NOUN grading table never contains the word NOUN, so grading pages from ABU, BUK and UNIZIK came back). The university name was stored in metadata but only the chunk text was embedded. Fix: detect the university in the question, filter to its files and replace the name with "the institution" in the embedded text. After the fix q10 ranked 1st, q18 1st and q09 4th. Evidence: `retrieval_eval_800_150_k4.csv` against `retrieval_eval_800_150_k4_filter.csv`.

## Generation failure example

Question q20: "Which cooking appliances does UNIZIK approve for use inside hostel rooms?" The top 4 passages included both chunks of `unizik_hostel_rules.pdf` PDF page 2 that state "Use of unauthorized electrical appliances is not permitted. Cooking in rooms is prohibited except in designated areas (where available)." The model still replied "Not enough information in the provided sources." It over-refused instead of correcting the false premise. Rewriting rules 3 and 4 of the prompt did not fix it at k=4. At k=6 the same question was answered correctly. We do not know why more passages helped. Evidence: `answer_eval_800_150_k4_filter_v2_prompt.json` (retrieved chunks and refusal) and `answer_eval_800_150_k6_filter_v2_prompt.csv`.

A second generation failure: in the v1 baseline run q11 gave correct numbers for three universities but no source tags, so the Sources list was empty. It passed in later runs.

## No-answer behaviour

The four unanswerable questions were refused with the exact sentence "Not enough information in the provided sources." in every run, with no citations: q14 (2022 World Cup), q15 (UNIZIK hostel fee, not stated), q16 (UNILORIN tuition amount, not stated) and q17 (2027 UTME fee, documents cover 2025 and 2026 only).

A similarity score cutoff would not have been enough. The out-of-scope question scored 0.27, but the in-domain unanswerable questions scored 0.52, 0.57 and 0.71, overlapping with correct answers (top scores 0.53 to 0.80). The refusal comes from the prompt instructions.

## Citation accuracy

In the final run every non-refused answer cited at least one expected page and used no tag that was not provided (this is part of the pass condition). The displayed Sources list is built from the retrieved pages by the code, so a fabricated file name or page cannot appear.