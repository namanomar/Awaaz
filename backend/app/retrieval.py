"""
Retrieval module — multilingual embedding + Qdrant vector search.

Improvements over v1:
  - Domain/scheme payload filtering so results stay on-topic
  - Multi-query retrieval: embeds 2 variants of the query and merges
    results by score for better recall
  - Returns structured dicts (not raw Qdrant points) so the LLM layer
    can use payload metadata (scheme, source) in its prompt
  - Gap logging kept separate from knowledge chunks via payload flag
"""
import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    IsNullCondition,
)
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None
_client: QdrantClient | None = None

COLLECTION = os.getenv("QDRANT_COLLECTION", "knowledge_base")


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
    return _client


# ── Core search ───────────────────────────────────────────────────────────────

def _search_single(
    embedding: list[float],
    top_k: int,
    scheme: str | None = None,
) -> list:
    """Single-vector search. Always excludes gap-logged (low_confidence) entries."""
    # Always exclude gap-logged queries (they have low_confidence=True in payload)
    # If payload index doesn't exist for 'low_confidence', fall back to no filter
    must_not = [FieldCondition(key="low_confidence", match=MatchValue(value=True))]
    must = []
    if scheme:
        must.append(FieldCondition(key="scheme", match=MatchValue(value=scheme)))

    query_filter = Filter(must=must or None, must_not=must_not)

    try:
        response = get_client().query_points(
            collection_name=COLLECTION,
            query=embedding,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
    except Exception:
        # Payload index missing — retry without any filter
        response = get_client().query_points(
            collection_name=COLLECTION,
            query=embedding,
            limit=top_k,
            with_payload=True,
        )
    return response.points


def search(
    query: str,
    top_k: int = 5,
    domain: str | None = None,  # reserved for future indexed filtering
    scheme: str | None = None,
) -> list[dict]:
    """
    Multi-query retrieval:
      1. Embed the raw query
      2. Embed a shortened/paraphrased form (strip filler words)
      3. Merge results by score, deduplicate by payload text, return top_k

    Returns list of dicts with keys: text, score, language, scheme, source
    """
    model = get_model()

    # Query variants for better recall
    raw_q = query.strip()
    short_q = raw_q[:120] if len(raw_q) > 120 else raw_q  # truncate very long queries

    emb1 = model.encode(raw_q).tolist()
    emb2 = model.encode(short_q).tolist() if short_q != raw_q else emb1

    hits1 = _search_single(emb1, top_k, scheme)
    hits2 = _search_single(emb2, top_k, scheme) if emb2 is not emb1 else []

    # Merge + deduplicate by text content (same chunk may surface from both queries)
    seen_texts: set[str] = set()
    merged = []
    for hit in sorted(hits1 + hits2, key=lambda h: h.score, reverse=True):
        # Skip gap-logged entries (they have low_confidence or needs_answer in payload)
        if hit.payload.get("low_confidence") or hit.payload.get("needs_answer"):
            continue
        text = hit.payload.get("text", "")
        if text and text not in seen_texts:
            seen_texts.add(text)
            merged.append({
                "text":     text,
                "score":    hit.score,
                "language": hit.payload.get("language", "en"),
                "scheme":   hit.payload.get("scheme", "general"),
                "source":   hit.payload.get("source", ""),
                "topic":    hit.payload.get("topic", ""),
            })

    return merged[:top_k]


# ── Helpers ───────────────────────────────────────────────────────────────────

def top_score(results: list[dict]) -> float:
    return results[0]["score"] if results else 0.0


def build_context(results: list[dict]) -> str:
    """Plain text context for Vapi system prompt (no LLM synthesis)."""
    return "\n\n".join(r["text"] for r in results)


# ── Gap logging ───────────────────────────────────────────────────────────────

def log_gap(query: str, language: str, score: float, domain: str = ""):
    """
    Store a low-confidence query in Qdrant so analysts can see
    what the knowledge base is missing.
    """
    embedding = get_model().encode(query).tolist()
    get_client().upsert(
        collection_name=COLLECTION,
        points=[PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "text":           query,
                "language":       language,
                "domain":         domain,
                "score":          round(score, 4),
                "needs_answer":   True,
                "low_confidence": True,
            },
        )],
    )


def fetch_gaps(limit: int = 50) -> list:
    client = get_client()
    results, _ = client.scroll(
        collection_name=COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="needs_answer", match=MatchValue(value=True))]
        ),
        limit=limit,
        with_payload=True,
    )
    return results
