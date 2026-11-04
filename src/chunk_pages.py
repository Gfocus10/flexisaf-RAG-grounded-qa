import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "data" / "extracted" / "pages.jsonl"
OUT_DIR = ROOT / "data" / "chunks"
MIN_CHUNK_CHARS = 30


def split_units(text, max_len):
    """Break page text into sentence-like units, hard-splitting any unit longer than max_len."""
    raw = re.split(r"(?<=[.!?])\s+|\n+", text)
    units = []
    for unit in raw:
        unit = unit.strip()
        if not unit:
            continue
        while len(unit) > max_len:
            units.append(unit[:max_len])
            unit = unit[max_len:]
        units.append(unit)
    return units


def chunk_text(text, chunk_size, overlap):
    """Pack units into chunks of at most chunk_size characters, carrying a small overlap."""
    units = split_units(text, chunk_size)
    chunks = []
    current = []
    current_len = 0

    for unit in units:
        added = len(unit) + (1 if current else 0)
        if current and current_len + added > chunk_size:
            chunks.append(" ".join(current))

            carry = []
            carry_len = 0
            for previous in reversed(current):
                if carry_len + len(previous) + 1 > overlap:
                    break
                carry.insert(0, previous)
                carry_len += len(previous) + 1

            current = carry
            current_len = sum(len(u) for u in current) + \
                max(len(current) - 1, 0)
            added = len(unit) + (1 if current else 0)

            if current_len + added > chunk_size:
                current = []
                current_len = 0
                added = len(unit)

        current.append(unit)
        current_len += added

    if current:
        chunks.append(" ".join(current))
    return chunks


def main():
    parser = argparse.ArgumentParser(
        description="Chunk extracted pages, keeping chunks inside page boundaries.")
    parser.add_argument("--chunk-size", type=int, default=800,
                        help="Max characters per chunk")
    parser.add_argument("--overlap", type=int, default=150,
                        help="Characters of overlap between chunks")
    args = parser.parse_args()

    if args.overlap >= args.chunk_size:
        raise SystemExit("overlap must be smaller than chunk-size")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"chunks_{args.chunk_size}_{args.overlap}.jsonl"

    per_doc = {}
    lengths = []

    with open(PAGES, encoding="utf-8") as src, open(out_path, "w", encoding="utf-8") as out:
        for line in src:
            page = json.loads(line)
            stem = Path(page["filename"]).stem
            index = 0
            for text in chunk_text(page["text"], args.chunk_size, args.overlap):
                if len(text) < MIN_CHUNK_CHARS:
                    continue
                record = {
                    "chunk_id": f"{stem}_p{page['page']:03d}_c{index:02d}",
                    "text": text,
                    "filename": page["filename"],
                    "title": page["title"],
                    "institution": page["institution"],
                    "category": page["category"],
                    "year": page["year"],
                    "page": page["page"],
                    "chunk_index": index,
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                per_doc[page["filename"]] = per_doc.get(
                    page["filename"], 0) + 1
                lengths.append(len(text))
                index += 1

    print(f"Settings: chunk_size={args.chunk_size}, overlap={args.overlap}")
    for name, count in per_doc.items():
        print(f"{name}: {count} chunks")
    print(f"Total chunks: {len(lengths)}")
    print(
        f"Chunk length (chars): min={min(lengths)}, avg={sum(lengths) // len(lengths)}, max={max(lengths)}")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
