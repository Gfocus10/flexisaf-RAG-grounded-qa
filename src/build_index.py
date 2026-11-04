import argparse
import json
import time
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
CHUNKS_DIR = ROOT / "data" / "chunks"
DB_DIR = ROOT / "chroma_db"
MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 64


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def main():
    parser = argparse.ArgumentParser(description="Embed chunks and store them in a Chroma collection.")
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=150)
    args = parser.parse_args()

    chunks_path = CHUNKS_DIR / f"chunks_{args.chunk_size}_{args.overlap}.jsonl"
    collection_name = f"uni_docs_{args.chunk_size}_{args.overlap}"

    with open(chunks_path, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]
    print(f"Loaded {len(chunks)} chunks from {chunks_path.name}")

    print(f"Loading embedding model {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)

    client = chromadb.PersistentClient(path=str(DB_DIR))
    try:
        client.delete_collection(collection_name)
        print(f"Replaced existing collection {collection_name}")
    except Exception:
        pass
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    start = time.time()
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        embeddings = model.encode(
            [c["text"] for c in batch],
            normalize_embeddings=True,
        ).tolist()
        collection.add(
            ids=[c["chunk_id"] for c in batch],
            documents=[c["text"] for c in batch],
            embeddings=embeddings,
            metadatas=[
                {
                    "filename": c["filename"],
                    "title": c["title"],
                    "institution": c["institution"],
                    "category": c["category"],
                    "year": to_int(c["year"]),
                    "page": c["page"],
                    "chunk_index": c["chunk_index"],
                }
                for c in batch
            ],
        )
        print(f"Indexed {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)}")

    elapsed = time.time() - start
    print(f"Collection {collection_name}: {collection.count()} chunks indexed in {elapsed:.0f}s")
    print(f"Saved to: {DB_DIR}")


if __name__ == "__main__":
    main()