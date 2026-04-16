from langdetect import detect, LangDetectException

SUPPORTED = {"hi", "en", "kn", "ta", "bn", "te", "mr"}


def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return lang if lang in SUPPORTED else "en"
    except LangDetectException:
        return "en"


def resolve_language(body: dict, query: str) -> str:
    """Prefer language from Vapi call metadata, fall back to langdetect."""
    vapi_lang = (
        body.get("call", {})
        .get("customer", {})
        .get("metadata", {})
        .get("language")
    )
    if vapi_lang:
        return vapi_lang
    return detect_language(query)
