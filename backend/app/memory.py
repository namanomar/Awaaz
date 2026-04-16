import os
import uuid
import hashlib
from datetime import datetime
from qdrant_client.models import PointStruct
from app.retrieval import get_model, get_client

COLLECTION = os.getenv("QDRANT_USER_COLLECTION", "user_memory")


def _phone_id(phone: str) -> str:
    return str(uuid.UUID(hashlib.md5(phone.encode()).hexdigest()))


def load_user_memory(phone: str) -> dict:
    client = get_client()
    try:
        response = client.query_points(
            collection_name=COLLECTION,
            query=get_model().encode(phone).tolist(),
            limit=1,
            with_payload=True,
        )
        results = response.points
        if results and results[0].score > 0.99:
            return results[0].payload
    except Exception:
        pass
    return {}


def save_user_memory(phone: str, updates: dict):
    client = get_client()
    existing = load_user_memory(phone)
    merged = {
        **existing,
        **updates,
        "phone": phone,
        "last_call": datetime.utcnow().isoformat(),
    }
    embedding = get_model().encode(str(merged)).tolist()
    point = PointStruct(id=_phone_id(phone), vector=embedding, payload=merged)
    client.upsert(collection_name=COLLECTION, points=[point])
