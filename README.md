# Awaaz — Voice AI for Public Services

> **"Ask government. Get answers."**
> A voice-first AI agent that lets anyone — regardless of literacy or language — access Indian government schemes by simply speaking.

Built for **HackBLR · Track 3: Voice AI for Accessibility & Societal Impact**

---

## What it does

Awaaz lets low-literacy and non-English-speaking users call or speak in their regional language and instantly get accurate answers about government schemes — no app, no reading, no forms.

- Speak in **Hindi, Tamil, Telugu, Kannada, Marathi, Bengali, Malayalam, or English**
- Get answers about **healthcare, agriculture, education, housing, employment, and social welfare**
- Works via **voice call** (Vapi) or **text chat** (web UI)
- Powered by **Gemini 2.5 Flash** + **Qdrant** semantic search

---

## Project structure

```
HackBLR/
├── frontend/          # Next.js 15 web UI (voice + chat interface)
└── backend/           # FastAPI webhook server (RAG pipeline)
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Voice | Vapi AI (STT + LLM + TTS) |
| Frontend | Next.js 15, React 19, Tailwind CSS 4, Framer Motion |
| Backend | FastAPI, Uvicorn |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers) |
| Vector DB | Qdrant Cloud |
| LLM | Google Gemini 2.5 Flash / OpenRouter Nemotron (fallback) |
| Deployment | Vercel (frontend) · HuggingFace Spaces (backend) |

---

## Live URLs

| Service | URL |
|---|---|
| Frontend | `https://awaaz.vercel.app` |
| Backend API | `https://namanomar-awaaz-backend.hf.space` |
| API Docs | `https://namanomar-awaaz-backend.hf.space/docs` |

---

## Running locally

### Prerequisites

- Node.js 18+
- Python 3.11+
- A [Vapi](https://vapi.ai) account with an assistant configured
- A [Qdrant Cloud](https://cloud.qdrant.io) cluster with the knowledge base ingested

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Copy and fill in your keys
cp .env.example .env

# Ingest FAQ data into Qdrant (first time only)
python scripts/ingest.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Copy and fill in your keys
cp .env.example .env.local

# Start the dev server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Environment variables

### Backend (`backend/.env`)

```env
QDRANT_URL=https://your-cluster.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=knowledge_base
QDRANT_USER_COLLECTION=user_memory
GEMINI_API_KEY=your_gemini_key
OPENROUTER_API_KEY=your_openrouter_key
VAPI_API_KEY=your_vapi_key
ESCALATION_THRESHOLD=0.42
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_VAPI_KEY=your_vapi_public_key
NEXT_PUBLIC_VAPI_ASSISTANT_ID=your_vapi_assistant_id
```

---

## Deployment

### Backend → HuggingFace Spaces (free)

1. Create a new Space with **Docker** SDK
2. Push the `backend/` folder to the Space repo
3. Add all backend env vars as **Secrets** in Space settings
4. The Dockerfile pre-downloads the embedding model at build time for fast cold starts

### Frontend → Vercel (free)

1. Push `frontend/` to a GitHub repo
2. Import it on [vercel.com/new](https://vercel.com/new)
3. Add the frontend env vars in Vercel project settings
4. Set `NEXT_PUBLIC_API_URL` to your HuggingFace Space URL

---

## Supported domains

| Domain | Schemes covered |
|---|---|
| Healthcare | Ayushman Bharat PMJAY, CGHS, ESIC |
| Agriculture | PM Kisan, PM Fasal Bima Yojana, Kisan Credit Card |
| Education | National Scholarship Portal, Pre/Post-Matric Scholarships |
| Housing | PMAY Urban, PMAY Gramin, DAY-NULM |
| Employment | MGNREGA, PM Kaushal Vikas Yojana, NCS Portal |
| Social Welfare | NSAP Pension, PM Ujjwala Yojana, Beti Bachao Beti Padhao |

---

## How it works

```
User speaks  →  Vapi STT  →  transcript
                                  ↓
                           FastAPI /webhook
                                  ↓
                    Qdrant semantic search (multilingual)
                                  ↓
                    Gemini 2.5 Flash synthesis
                                  ↓
                    Answer injected back via Vapi TTS
```

For text input, the browser calls `/webhook` directly — no voice pipeline needed.

---

## Languages supported

English · हिन्दी · தமிழ் · తెలుగు · मराठी · বাংলা · മലയാളം · ಕನ್ನಡ
