# Setting and prompt change log

1. 2026-11-02, initial design. Chunk size 800 characters, overlap 150, chunks kept inside page boundaries so citations point to one page. Minimum chunk length 30 characters. Embeddings: all-MiniLM-L6-v2 with cosine similarity in Chroma. Result: 2,555 chunks from 1,052 pages.

2. 2026-11-03, ground truth corrections. After reading the pages returned for failed questions, the expected sources of q11, q12 and q13 were widened: BUK pass mark text conflicts between the preface (40%) and the body (45%), UNILORIN page 32 repeats the 50% pass mark, UNIZIK page 35 and BUK page 17 state 75% attendance, and ABU page 19 defines probation. These corrections came from the content of the PDFs, not from what the search returned. The old results are kept as `evidence/v1_before_ground_truth_fix.csv`.

3. 2026-11-03, retrieval change: university filter. Detect a university named in the question, restrict the search to its files, and replace the name with "the institution" in the embedded text. Reason: the name matched introduction and title pages (q10, q18) and was missing from the answer chunk (q09). Effect on retrieval at k=4: 12 of 16 to 16 of 16.

4. 2026-11-03, top-k comparison. k=2 gave 14 of 16, k=4 gave 16 of 16, k=6 gave 16 of 16 with full coverage of q13.

5. 2026-11-03, `llm.py`. The `.env` file now overrides existing environment variables, because an old `GEMINI_MODEL` from the terminal session was silently overriding the project setting. Added a fallback model and short retries for temporary errors (503 and 429).

6. 2026-11-04, answer check corrections. q10 check now requires only the local transcript fee (the question asks only for that). q12 expected answer now includes BUK's general 75% rule. Both were mistakes in the checks, not model errors.

7. 2026-11-04, prompt change (v2). Rule 3 now refuses only when the sources do not state the specific information asked for, and rule 4 says that when the question assumes something the sources show to be false or restricted, the model should state what the sources say instead of refusing. Intended to fix q20. Result at k=4: q20 still refused, so the prompt change alone did not fix it.

8. 2026-11-04, citation safeguard. If a non-refused answer has no source tags, the code asks once more with a reminder, and flags the answer as uncited if it still has none. Added after q11 omitted citations in the baseline run. The test set did not trigger it, so its effect is untested. The v2 result of 18 of 20 at k=4 (q11 passing) was run-to-run variation and should not be credited to it.

9. 2026-11-04, default k changed from 4 to 6. At k=6 the v2 prompt passed 20 of 20, including q13 (all three universities) and q20.