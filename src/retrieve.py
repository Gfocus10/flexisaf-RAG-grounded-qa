import argparse
import re
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "chroma_db"
MODEL_NAME = "all-MiniLM-L6-v2"

FILE_GROUPS = {
    "abu": ["abu_examination_regulations_2023.pdf", "abu_student_handbook_2023_2024.pdf"],
    "buk": ["buk_general_exam_academic_regulations_2018.pdf"],
    "jamb": ["jamb_utme_manual_2025.pdf", "jamb_utme_manual_2026.pdf"],
    "noun": ["noun_ist_department_handbook_2026.pdf"],
    "udus": ["udus_students_handbook_2019_2020.pdf"],
    "unilorin": ["unilorin_postgraduate_handbook.pdf"],
    "unizik": ["unizik_general_academic_regulations.pdf", "unizik_hostel_rules.pdf"],
}

# Names that are removed from the embedded text once they are used as a filter.
NAME_ALIASES = {
    "abu": ["Ahmadu Bello University", "ABU"],
    "buk": ["Bayero University Kano", "Bayero University", "BUK"],
    "jamb": ["JAMB"],
    "noun": ["National Open University of Nigeria", "National Open University", "NOUN"],
    "udus": ["Usmanu Danfodiyo University", "UDUS"],
    "unilorin": ["University of Ilorin", "UNILORIN"],
    "unizik": ["Nnamdi Azikiwe University", "UNIZIK"],
}

# Words that trigger the filter but stay in the embedded text because they carry meaning.
FILTER_ONLY_TRIGGERS = {"jamb": ["UTME"]}

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_collection(chunk_size=800, overlap=150):
    client = chromadb.PersistentClient(path=str(DB_DIR))
    return client.get_collection(f"uni_docs_{chunk_size}_{overlap}")


def analyse_query(query):
    """Return (institution keys found in the question, text to embed)."""
    keys = []
    for key, names in NAME_ALIASES.items():
        triggers = names + FILTER_ONLY_TRIGGERS.get(key, [])
        if any(re.search(rf"\b{re.escape(n)}\b", query, re.I) for n in triggers):
            keys.append(key)

    text = query
    for key in keys:
        for name in sorted(NAME_ALIASES[key], key=len, reverse=True):
            text = re.sub(rf"\b{re.escape(name)}\b",
                          "the institution", text, flags=re.I)
    return keys, re.sub(r"\s+", " ", text).strip()


def retrieve(query, k=4, chunk_size=800, overlap=150, category=None, use_filter=True):
    """Return the top-k chunks for a query, each with a similarity score and source details."""
    keys, embed_text = analyse_query(query) if use_filter else ([], query)

    conditions = []
    if keys:
        files = [name for key in keys for name in FILE_GROUPS[key]]
        conditions.append({"filename": {"$in": files}})
    if category:
        conditions.append({"category": category})
    if len(conditions) > 1:
        where = {"$and": conditions}
    elif conditions:
        where = conditions[0]
    else:
        where = None

    collection = get_collection(chunk_size, overlap)
    embedding = get_model().encode(
        [embed_text], normalize_embeddings=True).tolist()
    result = collection.query(
        query_embeddings=embedding, n_results=k, where=where)

    hits = []
    for i in range(len(result["ids"][0])):
        hit = {
            "chunk_id": result["ids"][0][i],
            "text": result["documents"][0][i],
            "score": round(1 - result["distances"][0][i], 4),
        }
        hit.update(result["metadatas"][0][i])
        hits.append(hit)
    return hits


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Search the document index.")
    parser.add_argument("query")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--category", default=None)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument("--no-filter", action="store_true",
                        help="Turn off the institution filter")
    args = parser.parse_args()

    keys, embed_text = (
        [], args.query) if args.no_filter else analyse_query(args.query)
    hits = retrieve(args.query, args.k, args.chunk_size,
                    args.overlap, args.category, not args.no_filter)
    print(f"Query: {args.query}")
    print(f"Filter: {', '.join(keys) if keys else 'none'}")
    print(f"Embedded text: {embed_text}")
    print(f"Top {len(hits)} results\n")
    for rank, hit in enumerate(hits, start=1):
        snippet = hit["text"].replace("\n", " ")[:220]
        print(
            f"{rank}. score={hit['score']}  {hit['filename']}  page {hit['page']}  [{hit['category']}]")
        print(f"   {snippet}...\n")


if __name__ == "__main__":
    main()
