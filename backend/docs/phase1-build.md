# Phase 1 — Core voice agent (week 1–2)

Goal: working end-to-end voice agent. User calls → speaks in their language → gets an answer from the knowledge base.

## Step 1 — dependencies

```
# requirements.txt
vapi-python>=0.1
qdrant-client>=1.9
sentence-transformers>=2.7
fastapi>=0.110
uvicorn>=0.29
langdetect>=1.0.9
python-dotenv>=1.0
sqlalchemy>=2.0
pandas>=2.0
streamlit>=1.32
plotly>=5.18
httpx>=0.27
```

```bash
pip install -r requirements.txt
```

## Step 2 — Qdrant collection setup (`scripts/setup_qdrant.py`)

Run once to create collections.

```python
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
```

## Step 3 — ingest FAQs (`scripts/ingest.py`)

Place FAQ files in `data/faqs/`. Each file is plain text, one Q&A pair per paragraph:

```
Q: Ayushman Bharat ke liye kaun eligible hai?
A: Ayushman Bharat PMJAY yojana mein woh parivaar shamil hain jo SECC 2011 database mein hain. Har parivaar ko saal mein 5 lakh rupaye tak ka ilaj free milta hai.

Q: PMJAY card kaise banwayen?
A: Apne nazdiki Common Service Centre (CSC) ya empanelled hospital mein jayen. Ration card aur Aadhaar card saath le jayen.
```

```python
import os, uuid
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer
import argparse

load_dotenv()

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

def chunk_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    lang = path.stem.split("_")[0]          # e.g. hi_pmjay.txt → "hi"
    scheme = path.stem.split("_")[1] if "_" in path.stem else "general"
    return [{"text": b, "language": lang, "scheme": scheme, "source": path.name} for b in blocks]

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

    client.upsert(collection_name="knowledge_base", points=points)
    print(f"Upserted {len(points)} chunks from {len(files)} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/faqs/")
    args = parser.parse_args()
    ingest(args.data_dir)
```

```bash
python scripts/ingest.py --data-dir data/faqs/
```

## Step 4 — retrieval module (`app/retrieval.py`)

```python
import os
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

_model = None
_client = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model

def get_client():
    global _client
    if _client is None:
        _client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    return _client

def search(query: str, top_k: int = 3) -> list:
    embedding = get_model().encode(query).tolist()
    results = get_client().search(
        collection_name="knowledge_base",
        query_vector=embedding,
        limit=top_k,
        with_payload=True,
    )
    return results

def build_context(results: list) -> str:
    return "\n\n".join(r.payload["text"] for r in results)

def top_score(results: list) -> float:
    return results[0].score if results else 0.0
```

## Step 5 — FastAPI webhook (`app/main.py`)

```python
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.retrieval import search, build_context, top_score
from app.logger import log_call
from app.language import detect_language
from app.intent import classify_intent

load_dotenv()

app = FastAPI()
THRESHOLD = float(os.getenv("ESCALATION_THRESHOLD", 0.6))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/webhook")
async def vapi_webhook(req: Request):
    body = await req.json()

    # Extract query from Vapi function-call payload
    params = body.get("message", {}).get("functionCall", {}).get("parameters", {})
    query = params.get("query", "")
    call_info = body.get("call", {})
    call_id = call_info.get("id", "")
    phone = call_info.get("customer", {}).get("number", "")
    duration = call_info.get("duration", 0)

    if not query:
        return JSONResponse({"result": "I didn't catch that. Could you repeat?"})

    results = search(query)
    score = top_score(results)
    language = detect_language(query)
    intent = classify_intent(query)

    log_call({
        "call_id": call_id,
        "phone": phone,
        "language": language,
        "intent": intent,
        "query": query,
        "top_score": round(score, 4),
        "escalated": 1 if score < THRESHOLD else 0,
        "duration_s": duration,
    })

    if score < THRESHOLD:
        return JSONResponse({"result": "ESCALATE"})

    context = build_context(results)
    return JSONResponse({"result": context})
```

## Step 6 — language detection (`app/language.py`)

```python
from langdetect import detect, LangDetectException

SUPPORTED = {"hi", "en", "kn", "ta", "bn", "te", "mr"}

def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return lang if lang in SUPPORTED else "en"
    except LangDetectException:
        return "en"
```

## Step 7 — intent classifier (`app/intent.py`)

Simple keyword-based classifier for speed. Swap with zero-shot LLM classifier in Phase 2.

```python
INTENT_KEYWORDS = {
    "eligibility": ["eligible", "qualify", "entitled", "paatra", "yogya", "thagathu"],
    "documents":   ["document", "certificate", "proof", "kagaz", "praman", "certificate"],
    "appointment": ["appointment", "visit", "date", "samay", "mulakat"],
    "complaint":   ["complaint", "problem", "issue", "shikayat", "pareshani"],
}

def classify_intent(text: str) -> str:
    text_lower = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    return "other"
```

## Step 8 — Vapi assistant configuration

In the Vapi dashboard (dashboard.vapi.ai):

1. Create a new assistant
2. Set voice: `Neha` (Indian English) or `Riya` (Hindi)
3. Set transcriber language: `hi-IN` or `multi` for auto-detect
4. Add a **Function** tool named `retrieve_context`:
   ```json
   {
     "name": "retrieve_context",
     "description": "Retrieve relevant information from the knowledge base to answer the user's question.",
     "parameters": {
       "type": "object",
       "properties": {
         "query": { "type": "string", "description": "The user's question verbatim" }
       },
       "required": ["query"]
     }
   }
   ```
5. Set server URL to your webhook: `https://your-domain.com/webhook`
6. Paste system prompt from `docs/architecture.md`

## Step 9 — local dev test

```bash
# Terminal 1
uvicorn app.main:app --reload --port 8000

# Terminal 2 — expose to internet so Vapi can reach it
ngrok http 8000

# Copy the ngrok HTTPS URL into Vapi dashboard → Server URL
```

Test with a web call from the Vapi dashboard. Check FastAPI logs to confirm the webhook is being called and Qdrant is returning results.

## Checklist

- [ ] `.env` file created with all keys
- [ ] Qdrant collections created (`python scripts/setup_qdrant.py`)
- [ ] At least 20 FAQ chunks ingested (`python scripts/ingest.py`)
- [ ] FastAPI running locally
- [ ] ngrok exposing port 8000
- [ ] Vapi assistant configured with function tool + webhook URL
- [ ] End-to-end test call succeeds
- [ ] Retrieval score > 0.6 for common questions
