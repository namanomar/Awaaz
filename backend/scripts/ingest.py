"""Embed FAQ text files and upsert them into the Qdrant knowledge_base collection."""
import os
import uuid
import argparse
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

load_dotenv()

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))


def chunk_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    # Filename convention: <lang>_<scheme>.txt  e.g. hi_pmjay.txt or hi_pm_kisan.txt
    parts = path.stem.split("_", 1)  # split on first underscore only
    lang = parts[0]
    scheme = parts[1] if len(parts) > 1 else "general"
    return [
        {"text": b, "language": lang, "scheme": scheme, "source": path.name}
        for b in blocks
    ]


def ingest(data_dir: str):
    files = list(Path(data_dir).glob("*.txt"))
    if not files:
        print("No .txt files found in", data_dir)
        return

    all_chunks = []
    for f in files:
        all_chunks.extend(chunk_file(f))

    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=True)

    points = [
        PointStruct(id=str(uuid.uuid4()), vector=emb.tolist(), payload=meta)
        for emb, meta in zip(embeddings, all_chunks)
    ]

    client.upsert(collection_name=os.getenv("QDRANT_COLLECTION", "knowledge_base"), points=points)
    print(f"Upserted {len(points)} chunks from {len(files)} files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/faqs/")
    args = parser.parse_args()
    ingest(args.data_dir)
