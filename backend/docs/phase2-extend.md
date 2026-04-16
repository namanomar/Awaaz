# Phase 2 — Personalisation & multilingual (week 3–4)

Build on Phase 1. Add user memory across sessions, language-aware system prompts, smarter intent routing, and graceful escalation.

## Step 1 — per-user memory in Qdrant (`app/memory.py`)

```python
import os, uuid, hashlib
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from app.retrieval import get_model, get_client

COLLECTION = "user_memory"

def _phone_id(phone: str) -> str:
    return str(uuid.UUID(hashlib.md5(phone.encode()).hexdigest()))

def load_user_memory(phone: str) -> dict:
    client = get_client()
    try:
        results = client.search(
            collection_name=COLLECTION,
            query_vector=get_model().encode(phone).tolist(),
            limit=1,
            with_payload=True,
        )
        if results and results[0].score > 0.99:
            return results[0].payload
    except Exception:
        pass
    return {}

def save_user_memory(phone: str, updates: dict):
    client = get_client()
    existing = load_user_memory(phone)
    merged = {**existing, **updates, "phone": phone, "last_call": datetime.utcnow().isoformat()}

    embedding = get_model().encode(str(merged)).tolist()
    point = PointStruct(id=_phone_id(phone), vector=embedding, payload=merged)
    client.upsert(collection_name=COLLECTION, points=[point])
```

Integrate into `app/main.py`:

```python
from app.memory import load_user_memory, save_user_memory

@app.post("/webhook")
async def vapi_webhook(req: Request):
    body = await req.json()
    phone = body.get("call", {}).get("customer", {}).get("number", "")

    # Load memory at call start
    user_memory = load_user_memory(phone)

    # ... existing retrieval logic ...

    # Save any new facts extracted from this turn
    # (In production: use LLM to extract entities from the conversation)
    save_user_memory(phone, {
        "language": language,
        "last_intent": intent,
        "schemes_asked": user_memory.get("schemes_asked", []) + [intent],
    })

    return JSONResponse({"result": context, "user_memory": user_memory})
```

## Step 2 — language-aware system prompt injection

In the Vapi system prompt, use variables that your webhook populates:

```
You are a helpful assistant for government services.
Speak in {{language}} only unless the user switches.
User's name: {{user_name}}
Previous topics discussed: {{schemes_asked}}
Answer only from the context provided. Keep replies under 3 sentences.

Context:
{{context}}
```

Pass these as part of the `result` or use Vapi's variable injection via the function call response:

```python
return JSONResponse({
    "result": context,
    "variables": {
        "language": language,
        "user_name": user_memory.get("name", ""),
        "schemes_asked": ", ".join(user_memory.get("schemes_asked", [])),
    }
})
```

## Step 3 — language auto-detection & switching

Update `app/language.py` to use Vapi's metadata when available:

```python
def resolve_language(body: dict, query: str) -> str:
    # Vapi may pass language in call metadata
    vapi_lang = body.get("call", {}).get("customer", {}).get("metadata", {}).get("language")
    if vapi_lang:
        return vapi_lang
    # Fall back to langdetect
    return detect_language(query)
```

## Step 4 — LLM-based intent routing (optional upgrade)

Swap the keyword classifier with zero-shot classification:

```python
import openai, os, json

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INTENTS = ["eligibility_check", "document_help", "appointment_booking", "complaint", "other"]

def classify_intent_llm(query: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"Classify this query into one of {INTENTS}. Return only the intent label.\n\nQuery: {query}"
        }],
        max_tokens=20,
    )
    label = resp.choices[0].message.content.strip()
    return label if label in INTENTS else "other"
```

## Step 5 — escalation with Qdrant gap logging

Log low-confidence queries to a `low_confidence` filter so you can find content gaps:

```python
from qdrant_client.models import PointStruct
import uuid

def log_gap(query: str, language: str, score: float):
    client = get_client()
    embedding = get_model().encode(query).tolist()
    client.upsert(
        collection_name="knowledge_base",
        points=[PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "text": query,
                "language": language,
                "low_confidence": True,
                "score": score,
                "needs_answer": True,
            }
        )]
    )
```

Query gaps later:

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

gaps = client.scroll(
    collection_name="knowledge_base",
    scroll_filter=Filter(must=[FieldCondition(key="needs_answer", match=MatchValue(value=True))]),
    limit=50,
    with_payload=True,
)
```

## Step 6 — structured data collection (multi-turn form filling)

For eligibility checks, collect fields across turns using Vapi tool calls:

```python
# In Vapi dashboard, add a second tool:
{
  "name": "collect_eligibility_info",
  "description": "Collect user details needed to check scheme eligibility",
  "parameters": {
    "type": "object",
    "properties": {
      "age":         { "type": "integer" },
      "income_lpa":  { "type": "number" },
      "state":       { "type": "string" },
      "scheme":      { "type": "string" }
    }
  }
}
```

Handle in FastAPI:

```python
@app.post("/collect")
async def collect_info(req: Request):
    body = await req.json()
    params = body.get("message", {}).get("functionCall", {}).get("parameters", {})
    phone = body.get("call", {}).get("customer", {}).get("number", "")

    save_user_memory(phone, {
        "age": params.get("age"),
        "income_lpa": params.get("income_lpa"),
        "state": params.get("state"),
    })

    # Simple eligibility rule for PM-JAY
    eligible = params.get("income_lpa", 999) < 2.5
    result = "Aap PMJAY ke liye eligible hain." if eligible else "Aap is yojana ke liye eligible nahi hain."
    return JSONResponse({"result": result})
```

## Phase 2 checklist

- [ ] `app/memory.py` created and wired into webhook
- [ ] User memory saved on call end via Vapi end-of-call webhook (`POST /call-end`)
- [ ] Language detection upgraded to use Vapi metadata
- [ ] Intent routing tested across 5 languages
- [ ] Escalation with gap logging working
- [ ] Low-confidence query gaps visible in Streamlit dashboard
- [ ] At least one multi-turn form flow working (eligibility check)
