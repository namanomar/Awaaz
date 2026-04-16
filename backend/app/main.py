import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.retrieval import search, top_score, log_gap
from app.llm import generate_answer, active_provider
from app.language import resolve_language
from app.intent import classify_intent
from app.memory import load_user_memory, save_user_memory

load_dotenv()

app = FastAPI(title="Awaaz — Voice AI for Public Services")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

THRESHOLD = float(os.getenv("ESCALATION_THRESHOLD", 0.6))

DOMAINS = [
    {
        "id": "healthcare",
        "name": "Healthcare",
        "icon": "🏥",
        "description": "Ayushman Bharat PMJAY, hospital access, health cards",
        "schemes": ["Ayushman Bharat (PMJAY)", "CGHS", "ESIC"],
        "sample_questions": [
            "Who is eligible for Ayushman Bharat?",
            "How do I get a health card?",
            "Which hospitals accept PMJAY?",
        ],
    },
    {
        "id": "agriculture",
        "name": "Agriculture",
        "icon": "🌾",
        "description": "PM Kisan, crop insurance, farmer subsidies",
        "schemes": ["PM Kisan Samman Nidhi", "PM Fasal Bima Yojana", "Kisan Credit Card"],
        "sample_questions": [
            "When does PM Kisan installment come?",
            "How to register for PM Kisan?",
            "What is crop insurance process?",
        ],
    },
    {
        "id": "education",
        "name": "Education",
        "icon": "🎓",
        "description": "Scholarships, NSP portal, student loans",
        "schemes": ["National Scholarship Portal", "Pre-Matric Scholarship", "Post-Matric Scholarship"],
        "sample_questions": [
            "How to apply for scholarship?",
            "What documents are needed for NSP?",
            "What is the income limit for scholarship?",
        ],
    },
    {
        "id": "housing",
        "name": "Housing",
        "icon": "🏠",
        "description": "PM Awas Yojana, rural and urban housing schemes",
        "schemes": ["PMAY Urban", "PMAY Gramin", "DAY-NULM"],
        "sample_questions": [
            "How to apply for PM Awas Yojana?",
            "Who is eligible for free housing?",
            "What is the subsidy amount for home loan?",
        ],
    },
    {
        "id": "employment",
        "name": "Employment",
        "icon": "💼",
        "description": "MGNREGA, skill development, job portal",
        "schemes": ["MGNREGA", "PM Kaushal Vikas Yojana", "NCS Portal"],
        "sample_questions": [
            "How to get MGNREGA job card?",
            "What is the daily wage under MGNREGA?",
            "How to register on National Career Service portal?",
        ],
    },
    {
        "id": "social_welfare",
        "name": "Social Welfare",
        "icon": "🤝",
        "description": "Pension schemes, disability benefits, women welfare",
        "schemes": ["NSAP Pension", "PM Ujjwala Yojana", "Beti Bachao Beti Padhao"],
        "sample_questions": [
            "How to apply for old age pension?",
            "Who is eligible for widow pension?",
            "How to get free LPG connection?",
        ],
    },
]


@app.get("/")
async def root():
    return JSONResponse({"service": "Awaaz Voice API", "status": "ok"})


@app.get("/health")
def health():
    provider = active_provider()
    return {
        "status": "ok",
        "llm_provider": provider,
        "llm_configured": provider != "none",
        "qdrant_configured": bool(os.getenv("QDRANT_URL")),
    }


@app.get("/api/domains")
def get_domains():
    return {"domains": DOMAINS}


@app.get("/api/config")
def get_config():
    return {
        "vapi_public_key": os.getenv("VAPI_PUBLIC_KEY", ""),
        "vapi_assistant_id": os.getenv("VAPI_ASSISTANT_ID", ""),
    }


# ── Main webhook ──────────────────────────────────────────────────────────────

@app.post("/webhook")
async def vapi_webhook(req: Request):
    body = await req.json()

    # Support both Vapi function-call format and direct web client format
    func_params = (
        body.get("message", {})
        .get("functionCall", {})
        .get("parameters", {})
    )
    query = func_params.get("query", "") or body.get("query", "")
    domain = func_params.get("domain", "") or body.get("domain", "")

    call_info = body.get("call", {})
    call_id = call_info.get("id", "")
    phone = call_info.get("customer", {}).get("number", "")
    duration = call_info.get("duration", 0)

    if not query:
        return JSONResponse({"result": "I didn't catch that. Could you repeat?"})

    # Prefer language from function call params, then Vapi metadata, then auto-detect
    language = func_params.get("language") or body.get("language") or resolve_language(body, query)
    intent = classify_intent(query)
    user_memory = load_user_memory(phone) if phone and phone != "web-user" else {}

    # ── Retrieve from Qdrant (domain-filtered, multi-query) ───────────────────
    results = search(query, top_k=5, domain=domain or None)
    score = top_score(results)

    escalated = score < THRESHOLD

    if escalated:
        log_gap(query, language, score, domain=domain)
        return JSONResponse({"result": "ESCALATE", "score": round(score, 4)})

    # ── LLM synthesis ─────────────────────────────────────────────────────────
    # Pass top-5 chunks (already ranked by score) with their metadata to LLM
    answer = generate_answer(
        query=query,
        context_chunks=results[:5],
        language=language,
        user_memory=user_memory,
    )

    # Update user memory with this turn's facts
    if phone and phone != "web-user":
        schemes_asked = list(set(user_memory.get("schemes_asked", []) + [intent]))
        save_user_memory(phone, {
            "language": language,
            "last_intent": intent,
            "schemes_asked": schemes_asked,
        })

    return JSONResponse({
        "result": answer,
        "score": round(score, 4),
        "sources": [r["scheme"] for r in results[:3]],
        "variables": {
            "language": language,
            "user_name": user_memory.get("name", ""),
            "schemes_asked": ", ".join(user_memory.get("schemes_asked", [])),
        },
    })


# ── Eligibility multi-turn form ───────────────────────────────────────────────

@app.post("/collect")
async def collect_eligibility(req: Request):
    body = await req.json()
    params = (
        body.get("message", {})
        .get("functionCall", {})
        .get("parameters", {})
    )
    phone = body.get("call", {}).get("customer", {}).get("number", "")
    age = params.get("age", 0)
    income_lpa = params.get("income_lpa", 999)
    state = params.get("state", "")

    if phone:
        save_user_memory(phone, {"age": age, "income_lpa": income_lpa, "state": state})

    # Use LLM to give a human explanation of eligibility
    context = (
        f"PMJAY eligibility: families in SECC 2011 database, annual income below Rs 2.5 lakh are eligible. "
        f"No cap on family size. Coverage: Rs 5 lakh per year per family."
    )
    query = f"Am I eligible? Age={age}, income={income_lpa} LPA, state={state}"
    answer = generate_answer(
        query=query,
        context_chunks=[{"text": context, "scheme": "pmjay", "source": "eligibility_rules"}],
        language="en",
        user_memory={},
    )
    return JSONResponse({"result": answer})


@app.post("/call-end")
async def call_end(req: Request):
    body = await req.json()
    phone = body.get("call", {}).get("customer", {}).get("number", "")
    if phone:
        save_user_memory(phone, {"call_ended": True})
    return JSONResponse({"status": "ok"})
