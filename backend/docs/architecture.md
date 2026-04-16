# Architecture

## System overview

```
User (phone/web)
    │  voice
    ▼
┌─────────────────────────┐
│         Vapi            │
│  STT → LLM → TTS        │
│  Multilingual           │
│  Phone number / widget  │
└────────┬────────────────┘
         │ POST /webhook  (transcribed query)
         ▼
┌─────────────────────────┐
│       FastAPI           │
│  1. embed query         │
│  2. search Qdrant       │
│  3. build context str   │
│  4. log_call() to DB    │
│  5. return {context}    │
└────────┬────────────────┘
         │ vector search
         ▼
┌─────────────────────────┐
│        Qdrant           │
│  collection: knowledge  │  ← FAQ chunks, multilingual embeddings
│  collection: users      │  ← per-caller memory, keyed by phone
└─────────────────────────┘

         ┌─────────────────┐
         │   SQLite DB     │  ← call logs (language, intent, score, duration)
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │    Streamlit    │  ← analytics dashboard
         └─────────────────┘
```

## Data flow — one call turn

1. User speaks → Vapi transcribes (STT)
2. Vapi POST to `POST /webhook` with `{ message: { content: "..." }, call: { id, customer: { number } } }`
3. FastAPI embeds the query with `paraphrase-multilingual-MiniLM-L12-v2`
4. Qdrant nearest-neighbour search on `knowledge_base`, top-3 results
5. If `top_score >= 0.60`: build context string, return to Vapi
6. If `top_score < 0.60`: return escalation signal; Vapi transfers call
7. On call start: look up `user_memory` by phone number, inject past facts into system prompt
8. On call end (Vapi end-of-call webhook): upsert new facts to `user_memory`
9. `log_call()` writes one row to SQLite at every turn

## Vapi webhook payload (inbound)

```json
{
  "message": {
    "type": "function-call",
    "functionCall": {
      "name": "retrieve_context",
      "parameters": { "query": "Ayushman Bharat ke liye eligible kaun hai?" }
    }
  },
  "call": {
    "id": "call_abc123",
    "customer": { "number": "+919876543210" },
    "duration": 47
  }
}
```

## Vapi webhook response (outbound)

```json
{
  "result": "Ayushman Bharat (PMJAY) covers families below poverty line. Annual cover is ₹5 lakh per family. To check eligibility visit pmjay.gov.in or call 14555."
}
```

## Qdrant collections

### `knowledge_base`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | chunk id |
| `vector` | float[] | 384-dim, MiniLM-L12 |
| `payload.text` | str | the answer chunk |
| `payload.language` | str | `hi`, `en`, `kn`, `ta`, `bn` |
| `payload.topic` | str | `eligibility`, `documents`, `process` |
| `payload.source` | str | URL or doc name |
| `payload.scheme` | str | `pmjay`, `pm_kisan`, `scholarship` |

### `user_memory`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | derived from phone hash |
| `vector` | float[] | embedding of user summary |
| `payload.phone` | str | hashed phone number |
| `payload.name` | str | collected during call |
| `payload.language` | str | preferred language |
| `payload.schemes_asked` | list[str] | schemes user has enquired about |
| `payload.last_call` | datetime | |
| `payload.notes` | str | freeform facts from last call |

## Embedding model

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

- 384 dimensions
- Languages: Hindi, English, Kannada, Tamil, Bengali, + 50 others
- ~120ms per batch of 32 on CPU — fast enough for real-time webhook use
- Load once at startup, keep in memory

## Escalation logic

```python
TOP_K = 3
THRESHOLD = float(os.getenv("ESCALATION_THRESHOLD", 0.6))

results = qdrant_client.search(collection_name="knowledge_base", query_vector=embedding, limit=TOP_K)
top_score = results[0].score if results else 0.0

if top_score < THRESHOLD:
    log_call({..., "escalated": 1})
    return {"result": "ESCALATE"}   # Vapi reads this and transfers call
```

## Vapi system prompt template

```
You are a helpful government services assistant. Speak clearly and simply. Use short sentences.
Confirm before giving important advice. If you are not sure, say "Main pata karta hoon" (I will find out).

User's language: {{language}}
User's name: {{user_name}}
Past context: {{user_memory}}

Relevant information:
{{context}}

Rules:
- Never make up information not in the context above.
- If context is empty, say you will connect them to someone who can help.
- Keep each response under 3 sentences.
```
