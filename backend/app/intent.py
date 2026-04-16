import os

INTENT_KEYWORDS = {
    "eligibility": ["eligible", "qualify", "entitled", "paatra", "yogya", "thagathu"],
    "documents":   ["document", "certificate", "proof", "kagaz", "praman"],
    "appointment": ["appointment", "visit", "date", "samay", "mulakat"],
    "complaint":   ["complaint", "problem", "issue", "shikayat", "pareshani"],
}


def classify_intent(text: str) -> str:
    text_lower = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    return "other"


# Optional LLM-based classifier (Phase 2) — only used if OPENAI_API_KEY is set
def classify_intent_llm(query: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return classify_intent(query)

    import openai, json

    client = openai.OpenAI(api_key=api_key)
    INTENTS = ["eligibility", "documents", "appointment", "complaint", "other"]

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": (
                f"Classify this query into one of {INTENTS}. "
                f"Return only the intent label.\n\nQuery: {query}"
            ),
        }],
        max_tokens=20,
    )
    label = resp.choices[0].message.content.strip()
    return label if label in INTENTS else "other"
