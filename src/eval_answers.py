import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

from rag import answer

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "data" / "eval_questions.json"
CHECKS = ROOT / "data" / "answer_checks.json"
OUT_DIR = ROOT / "evidence"
CLARIFY = re.compile(
    r"which (university|institution)|please (specify|tell)|could you (specify|clarify)", re.I)


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Evaluate generated answers on the 20 questions.")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument("--no-filter", action="store_true")
    parser.add_argument("--pause", type=float, default=4.0,
                        help="Seconds to wait between questions")
    parser.add_argument("--label", default="",
                        help="Optional text added to the output file names")
    args = parser.parse_args()

    with open(QUESTIONS, encoding="utf-8") as f:
        questions = json.load(f)
    with open(CHECKS, encoding="utf-8") as f:
        checks = json.load(f)

    rows = []
    details = []
    for index, q in enumerate(questions):
        try:
            res = answer(q["question"], args.k, args.chunk_size,
                         args.overlap, not args.no_filter)
        except Exception as error:
            res = {
                "answer": f"ERROR: {error}", "refused": False, "citations": [],
                "invalid_tags": [], "model": "", "retrieved": [],
            }
            errored = True
        else:
            errored = False

        text = res["answer"]
        expected = {(s["filename"], s["page"]) for s in q["expected_sources"]}
        cited = {(c["filename"], c["page"]) for c in res["citations"]}
        keywords_ok = all(re.search(p, text, re.I)
                          for p in checks.get(q["id"], []))
        clarifies = bool(CLARIFY.search(text))
        citation_ok = bool(expected & cited) if expected else not cited
        invalid = bool(res["invalid_tags"])

        if q["type"] == "unanswerable":
            refusal_ok = res["refused"]
            passed = refusal_ok
        else:
            refusal_ok = not res["refused"]
            if q["type"] == "ambiguous":
                passed = refusal_ok and (clarifies or (
                    keywords_ok and citation_ok)) and not invalid
            else:
                passed = refusal_ok and keywords_ok and citation_ok and not invalid
        if errored:
            passed = False

        result = "PASS" if passed else "FAIL"
        pages = "; ".join(
            f"{c['filename']} p{c['page']}" for c in res["citations"])
        rows.append({
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "answer": text,
            "refused": res["refused"],
            "cited_pages": pages,
            "refusal_ok": refusal_ok,
            "keywords_ok": keywords_ok,
            "citation_ok": citation_ok,
            "invalid_tags": " ".join(map(str, res["invalid_tags"])),
            "result": result,
            "model": res["model"],
            "human_check": "",
        })
        details.append({"id": q["id"], "question": q["question"], **res})
        print(
            f"{q['id']} {q['type']:<12} refused={res['refused']!s:<5} "
            f"keywords={keywords_ok!s:<5} citation={citation_ok!s:<5} {result}"
        )
        if index < len(questions) - 1:
            time.sleep(args.pause)

    OUT_DIR.mkdir(exist_ok=True)
    stem = f"answer_eval_{args.chunk_size}_{args.overlap}_k{args.k}"
    stem += "" if args.no_filter else "_filter"
    stem += f"_{args.label}" if args.label else ""
    csv_path = OUT_DIR / f"{stem}.csv"
    json_path = OUT_DIR / f"{stem}.json"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)

    print(
        f"\nSettings: chunk_size={args.chunk_size}, overlap={args.overlap}, k={args.k}, filter={not args.no_filter}")
    for kind in ("answerable", "ambiguous", "misleading", "unanswerable"):
        group = [r for r in rows if r["type"] == kind]
        passed = sum(1 for r in group if r["result"] == "PASS")
        print(f"{kind}: {passed}/{len(group)} passed")
    print(
        f"Total: {sum(1 for r in rows if r['result'] == 'PASS')}/{len(rows)} passed")
    print(f"Saved: {csv_path}")
    print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
