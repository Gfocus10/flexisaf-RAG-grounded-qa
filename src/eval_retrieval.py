import argparse
import csv
import json
import sys
from pathlib import Path

from retrieve import retrieve

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "data" / "eval_questions.json"
OUT_DIR = ROOT / "evidence"


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Evaluate retrieval on the 20 evaluation questions.")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument("--no-filter", action="store_true", help="Turn off the institution filter (baseline)")
    args = parser.parse_args()

    with open(QUESTIONS, encoding="utf-8") as f:
        questions = json.load(f)

    rows = []
    details = []
    for q in questions:
        hits = retrieve(q["question"], args.k, args.chunk_size, args.overlap, use_filter=not args.no_filter)
        retrieved = [(h["filename"], h["page"]) for h in hits]
        expected = [(s["filename"], s["page"]) for s in q["expected_sources"]]
        found = [e for e in expected if e in retrieved]
        ranks = [retrieved.index(e) + 1 for e in found]
        first_rank = min(ranks) if ranks else None

        if expected:
            result = "PASS" if found else "FAIL"
        else:
            result = "n/a"

        top_score = hits[0]["score"] if hits else 0.0
        rows.append({
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "top_score": top_score,
            "expected_total": len(expected),
            "expected_found": len(found),
            "first_rank": first_rank if first_rank else "",
            "result": result,
            "retrieved": " | ".join(
                f"{h['filename']} p{h['page']} ({h['score']})" for h in hits
            ),
        })
        details.append({
            "id": q["id"],
            "question": q["question"],
            "expected_sources": q["expected_sources"],
            "retrieved": [
                {
                    "chunk_id": h["chunk_id"],
                    "filename": h["filename"],
                    "page": h["page"],
                    "score": h["score"],
                    "text": h["text"],
                }
                for h in hits
            ],
        })
        print(
            f"{q['id']} {q['type']:<12} top={top_score:.3f} "
            f"found {len(found)}/{len(expected)} rank={first_rank} {result}"
        )

    OUT_DIR.mkdir(exist_ok=True)
    stem = f"retrieval_eval_{args.chunk_size}_{args.overlap}_k{args.k}" + ("" if args.no_filter else "_filter")
    csv_path = OUT_DIR / f"{stem}.csv"
    json_path = OUT_DIR / f"{stem}.json"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)

    print(
        f"\nSettings: chunk_size={args.chunk_size}, overlap={args.overlap}, k={args.k}")
    for kind in ("answerable", "ambiguous", "misleading", "unanswerable"):
        group = [r for r in rows if r["type"] == kind]
        if not group:
            continue
        avg_top = sum(r["top_score"] for r in group) / len(group)
        if kind == "unanswerable":
            print(f"{kind}: {len(group)} questions, average top score {avg_top:.3f}")
        else:
            passed = sum(1 for r in group if r["result"] == "PASS")
            print(
                f"{kind}: {passed}/{len(group)} found an expected page in the top {args.k}, average top score {avg_top:.3f}")
    print(f"Saved: {csv_path}")
    print(f"Saved: {json_path}")


if __name__ == "__main__":
    main()
