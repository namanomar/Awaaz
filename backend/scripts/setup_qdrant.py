"""Run once to create Qdrant collections."""
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

load_dotenv()

client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

client.recreate_collection(
    collection_name="knowledge_base",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

client.recreate_collection(
    collection_name="user_memory",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

print("Collections created.")
