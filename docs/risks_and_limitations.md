# Risks and limitations

## Hallucination and prompt dependence

The model is told to answer only from the sources, but that is an instruction, not a guarantee. I saw it omit citations once (q11) and refuse a question whose answer was in the retrieved text (q20). The automatic checks look for key numbers and cited pages, so they can miss a wrong explanation around a correct number. The Sources list is built from retrieved pages by the code, but a cited page does not prove the sentence next to it is faithful.

## Refusal cannot rely on similarity scores

In-domain questions whose answer is missing (hostel fee, tuition, 2027 UTME fee) scored 0.52 to 0.71, the same range as correct answers. Only the prompt stops them from being answered.

## Incomplete answers on questions that name no university

The university filter only works when the question names one, and the alias list is written by hand for seven institutions. Without it the answer can cover only some universities (q13 at k=4 omitted UNIZIK).

## Evaluation limits

Only 20 questions, written by the same people who tuned the system, so the results are optimistic. Each configuration was run once and the model is not fully repeatable (q11 passed, failed and passed again across runs). The automatic key fact checks are rough patterns, and i reviewed the answers myself.

## Document and extraction problems

1. Page-bounded chunks mean an answer that spans two pages can be missed.
2. Some PDFs lost spaces or characters in extraction (the ABU handbook and UNILORIN handbook have words run together, the BUK regulations lost "fi" ligatures). This reduces embedding quality and makes some quoted text look odd.
3. Citations use PDF page positions, not printed page numbers, which differ in several files.
4. The documents contradict themselves in places (BUK pass mark 40% in the preface, 45% in the body).
5. The JAMB files are manuals for examination officials, not guidance for candidates.

## Freshness

The documents are dated from 2018 to 2026 and rules change. I do not know whether a regulation is still in force, and answers must not be treated as official guidance. The 2025 and 2026 JAMB manuals are almost identical, and the year in a question cannot always separate them.

## Privacy and permissions

The documents are public and contain no personal data, but the register notes that no explicit reuse licence was found, so they are included only as sample documents for this assignment. Questions and retrieved passages are sent to Google's Gemini API. Google states that free-tier usage may be used to improve its products, so private documents or personal questions should not be used with this setup. The API key lives in `.env`, which is excluded from git.

## Cost and latency

The free tier has rate limits and models can be busy (503 and 429 errors occurred). The code retries and can fall back to a second model. Each question sends about six passages of at most 800 characters. Building the index took about 4 to 5 minutes on CPU and the answer evaluation takes about 2 minutes with a deliberate pause between questions.