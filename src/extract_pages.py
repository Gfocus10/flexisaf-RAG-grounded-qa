import csv
import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
REGISTER = ROOT / "data" / "document_register.csv"
OUT = ROOT / "data" / "extracted" / "pages.jsonl"


def clean(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTER, newline="", encoding="utf-8-sig") as f:
        register = list(csv.DictReader(f))

    total_pages = 0
    with open(OUT, "w", encoding="utf-8") as out:
        for row in register:
            reader = PdfReader(RAW_DIR / row["filename"])
            n_pages = len(reader.pages)
            empty = 0
            chars = 0
            for page_no, page in enumerate(reader.pages, start=1):
                text = clean(page.extract_text() or "")
                if not text:
                    empty += 1
                    continue
                chars += len(text)
                record = {
                    "filename": row["filename"],
                    "title": row["title"],
                    "institution": row["institution"],
                    "category": row["category"],
                    "year": row["year"],
                    "page": page_no,
                    "text": text,
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
            total_pages += n_pages - empty
            print(
                f"{row['filename']}: {n_pages} pages, {empty} empty, {chars} chars")

    print(f"Total pages with text: {total_pages}")


if __name__ == "__main__":
    main()
