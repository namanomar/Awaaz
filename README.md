<div align="center">

# 🎙️ Awaaz — आवाज

### Voice AI for Public Services

**Ask any government question. Get an answer — in your language.**

*Built for HackBLR 2026 · Track 3: Voice AI for Accessibility & Societal Impact*

---

[![Frontend](https://img.shields.io/badge/Frontend-awaaz--orpin.vercel.app-black?style=for-the-badge&logo=vercel)](https://awaaz-orpin.vercel.app)
[![Backend](https://img.shields.io/badge/Backend-HuggingFace%20Spaces-orange?style=for-the-badge&logo=huggingface)](https://namanomar-awaaz-backend.hf.space/docs)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

</div>

---

## The Problem

Over **300 million** Indians are functionally illiterate. **73%** of rural India speaks no English. Government welfare portals are text-heavy, English-only, and impossible to navigate without a smartphone or education. Billions in welfare benefits go unclaimed every year — not because people don't qualify, but because they simply can't access the information.

## The Solution

Awaaz is a **voice-first AI agent** that makes government scheme information accessible to everyone. Speak naturally in your language, get a plain-language answer read back to you. No app. No reading. No forms.

```
You say:  "PM Kisan ka paisa kab aata hai?"
Awaaz:    "PM Kisan Samman Nidhi ke tahat ₹6000 teen installments
           mein aate hain — April, August, aur December mein."
```

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🗣️ | **Voice-first** | Tap mic, speak naturally — no typing required |
| 🌐 | **8 Indian languages** | Hindi, Tamil, Telugu, Kannada, Marathi, Bengali, Malayalam, English |
| ⚡ | **Real-time streaming** | Transcript appears word-by-word as the assistant speaks |
| 🏛️ | **6 government domains** | Healthcare, Agriculture, Education, Housing, Employment, Social Welfare |
| 💬 | **Text fallback** | Full chat interface when voice isn't convenient |
| 🔗 | **Smart link rendering** | Spoken URLs auto-converted to clickable links |
| 🛡️ | **Safe escalation** | Low-confidence answers route to helpline 14555, never guesses |
| 🌙 | **Dark / Light mode** | Full theme support |

---

## 🏛️ Government Domains Covered

| Domain | Schemes |
|---|---|
| 🏥 Healthcare | Ayushman Bharat PMJAY · CGHS · ESIC |
| 🌾 Agriculture | PM Kisan Samman Nidhi · PM Fasal Bima Yojana · Kisan Credit Card |
| 🎓 Education | National Scholarship Portal · Pre-Matric · Post-Matric Scholarships |
| 🏠 Housing | PMAY Urban · PMAY Gramin · DAY-NULM |
| 💼 Employment | MGNREGA · PM Kaushal Vikas Yojana · NCS Portal |
| 🤝 Social Welfare | NSAP Pension · PM Ujjwala Yojana · Beti Bachao Beti Padhao |

Each domain has **10–15 curated Q&A pairs** organised by topic with suggested questions built into the UI.

---

## 🌐 Languages

| Language | Script | STT Support |
|---|---|---|
| English | English | ✅ Deepgram native |
| Hindi | हिन्दी | ✅ Deepgram native |
| Tamil | தமிழ் | ✅ Deepgram native |
| Kannada | ಕನ್ನಡ | ✅ Deepgram native |
| Telugu | తెలుగు | 🔄 Auto-detect |
| Marathi | मराठी | 🔄 Auto-detect |
| Bengali | বাংলা | 🔄 Auto-detect |
| Malayalam | മലയാളം | 🔄 Auto-detect |

Multilingual embeddings use `paraphrase-multilingual-MiniLM-L12-v2` — all 8 languages share a single vector space.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User                                  │
│           speaks / types a question                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │       Vapi AI           │  ← STT: Deepgram nova-3
          │  (voice call layer)     │  ← TTS: speaks answer back
          └────────────┬────────────┘
                       │  POST /webhook
          ┌────────────▼────────────┐
          │    FastAPI Backend      │  ← hosted on HuggingFace Spaces
          │                         │
          │  1. Detect language     │
          │  2. Classify intent     │
          │  3. Embed query         │
          │  4. Search Qdrant       │  ← multilingual vector DB
          │  5. Score confidence    │  ← escalate if score < 0.42
          │  6. Synthesise answer   │  ← Gemini 2.5 Flash
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │   Answer returned       │  plain language, correct language
          └─────────────────────────┘
```

For **text input**, the browser calls `/webhook` directly — bypassing the voice layer entirely.

---

## 🛠️ Tech Stack

### Frontend
- **Framework:** Next.js 15 + React 19
- **Styling:** Tailwind CSS 4 + Framer Motion
- **Voice:** Vapi Web SDK (`@vapi-ai/web`)
- **Language:** TypeScript

### Backend
- **API:** FastAPI + Uvicorn
- **Vector DB:** Qdrant Cloud
- **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers)
- **LLM:** Google Gemini 2.5 Flash · OpenRouter Nemotron (fallback)
- **Language detection:** langdetect

### Infrastructure
- **Frontend:** Vercel (free tier, auto-deploys on push)
- **Backend:** HuggingFace Spaces (Docker, free tier)

---

## 🚀 Live URLs

| | URL |
|---|---|
| 🌐 Web App | https://awaaz-orpin.vercel.app |
| 🔌 Backend API | https://namanomar-awaaz-backend.hf.space |
| 📖 API Docs | https://namanomar-awaaz-backend.hf.space/docs |

---

## 📁 Project Structure

```
HackBLR/
├── frontend/                    # Next.js web app
│   ├── app/
│   │   ├── page.tsx             # Landing page — domain selector
│   │   └── voice/
│   │       ├── page.tsx
│   │       └── VoiceInterface.tsx   # Main voice + chat UI
│   ├── components/
│   │   ├── layout/Navbar.tsx
│   │   └── voice/
│   │       ├── ChatArea.tsx     # Message thread + URL rendering
│   │       └── VoiceOrb.tsx     # Mic button (unused after redesign)
│   └── lib/
│       └── domains.ts           # All domains, schemes & question groups
│
├── backend/                     # FastAPI RAG server
│   ├── app/
│   │   ├── main.py              # API endpoints
│   │   ├── retrieval.py         # Qdrant search
│   │   ├── llm.py               # Gemini / OpenRouter synthesis
│   │   ├── language.py          # Language detection
│   │   ├── intent.py            # Intent classification
│   │   ├── memory.py            # Per-user memory (Qdrant)
│   │   └── prompts.py           # System prompts
│   ├── scripts/
│   │   └── ingest.py            # Embed & upsert FAQs to Qdrant
│   ├── data/faqs/               # Raw FAQ data by domain
│   ├── Dockerfile
│   └── requirements.txt
│
├── README.md
└── awaaz-pitch.html             # HTML pitch deck (open in browser)
```

---

## ⚙️ Running Locally

### Prerequisites
- Node.js 18+, Python 3.11+
- [Vapi](https://vapi.ai) account with an assistant set up
- [Qdrant Cloud](https://cloud.qdrant.io) cluster with data ingested

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Fill in QDRANT_URL, QDRANT_API_KEY, GEMINI_API_KEY, etc.

# Ingest FAQ knowledge base into Qdrant (first time only)
python scripts/ingest.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend

npm install

# Set up environment variables
cp .env.example .env.local
# Fill in NEXT_PUBLIC_VAPI_KEY, NEXT_PUBLIC_VAPI_ASSISTANT_ID
# Set NEXT_PUBLIC_API_URL=http://localhost:8000 for local backend

npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## 🔑 Environment Variables

### `backend/.env`

```env
# Qdrant (vector database)
QDRANT_URL=https://your-cluster.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=knowledge_base
QDRANT_USER_COLLECTION=user_memory

# LLM providers
GEMINI_API_KEY=your_gemini_api_key
OPENROUTER_API_KEY=your_openrouter_api_key   # fallback

# Vapi
VAPI_API_KEY=your_vapi_api_key

# Tuning
ESCALATION_THRESHOLD=0.42    # below this score → escalate to helpline
```

### `frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=https://namanomar-awaaz-backend.hf.space
NEXT_PUBLIC_VAPI_KEY=your_vapi_public_key
NEXT_PUBLIC_VAPI_ASSISTANT_ID=your_vapi_assistant_id
```

---

## ☁️ Deployment (Free Tier)

### Backend → HuggingFace Spaces

```bash
cd backend
git init
git remote add origin https://huggingface.co/spaces/YOUR_USERNAME/awaaz-backend
git add . && git commit -m "deploy"
git push origin main
```

Then go to **Space Settings → Secrets** and add all backend env vars.

> The Dockerfile pre-downloads the embedding model (~400MB) at build time so cold starts are instant.

### Frontend → Vercel

1. Push `frontend/` to GitHub
2. Import at [vercel.com/new](https://vercel.com/new)
3. Add env vars in Vercel project settings
4. Make sure `NEXT_PUBLIC_API_URL` points to your HuggingFace Space URL

> **Note:** HuggingFace free tier sleeps after 15 min of inactivity. First request after sleep takes ~30s to wake up.

---

## 🧪 Testing the API

```bash
# Health check
curl https://namanomar-awaaz-backend.hf.space/health

# Test webhook
curl -s -X POST https://namanomar-awaaz-backend.hf.space/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": { "functionCall": { "parameters": {
      "query": "Who is eligible for Ayushman Bharat?",
      "domain": "healthcare"
    }}},
    "call": { "id": "test-001", "customer": { "number": "web-user" }, "duration": 0 }
  }' | python3 -m json.tool
```

---

<div align="center">

**Every citizen deserves to know their rights. Now they can just ask.**

Made with ❤️ at HackBLR 

</div>
