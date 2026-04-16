"""
LLM synthesis — two-provider chain:
  Primary:  Google Gemini 2.5 Flash (via google-genai SDK, GEMINI_API_KEY)
  Fallback: OpenRouter Nemotron (OPENROUTER_API_KEY)

Gemini 2.5 Flash is fast and clean; Nemotron is the safety net.
"""
import os
import re
from app.prompts import WEBHOOK_SYSTEM_PROMPT as SYSTEM_PROMPT

# ── Gemini (primary) ──────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"

# ── OpenRouter Nemotron (fallback) ────────────────────────────────────────────
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
FALLBACK_MODEL  = "nvidia/nemotron-3-super-120b-a12b:free"

# Phrases that indicate CoT reasoning leaking from reasoning models
_REASONING_PATTERNS = re.compile(
    r"^(we need|we must|we can|we have|let'?s |let me |from context|from chunk|"
    r"the context|the question|that'?s |this is |so we |so the |so let|so answer|"
    r"first,|also,|could |would |should |must |it'?s |it is |note:|rule:|"
    r"check |ensure |provide |craft:|write:|answer:|response:|here we need|"
    r"chunk \d|based on|now,|then,|and then|however|therefore|"
    r"already |actually |basically |essentially )",
    re.IGNORECASE,
)


def _is_reasoning(sentence: str) -> bool:
    return bool(_REASONING_PATTERNS.match(sentence.strip()))


def _extract_answer(raw: str) -> str:
    """Extract the spoken answer, handling CoT leakage from reasoning models.
    The actual answer tends to be at the END of reasoning model output.
    """
    if not raw:
        return raw

    # 1. Try explicit <answer> tag
    m = re.search(r"<answer>(.*?)</answer>", raw, re.DOTALL)
    if m:
        return m.group(1).strip()

    # 2. Longest quoted string > 80 chars (model often quotes the final answer)
    quotes = re.findall(r'"([^"]{80,600})"', raw)
    if quotes:
        best = max(quotes, key=len)
        if not _is_reasoning(best):
            return best.strip()

    # 3. Reverse-scan sentences — answer is at END, reasoning at START
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', raw) if s.strip() and len(s.strip()) > 20]
    collected = []
    for sent in reversed(sentences):
        if _is_reasoning(sent):
            break
        collected.insert(0, sent)
        if len(collected) >= 3:
            break

    if collected and not all(_is_reasoning(s) for s in collected):
        return " ".join(collected)

    # 4. Last resort: last non-empty paragraph
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    return paragraphs[-1] if paragraphs else raw


def _build_prompt(query: str, context_chunks: list[dict], language: str, user_memory: dict) -> str:
    formatted = []
    for i, chunk in enumerate(context_chunks, 1):
        scheme = chunk.get("scheme", "general")
        source = chunk.get("source", "")
        text = chunk.get("text", "")
        formatted.append(f"[Chunk {i} | scheme={scheme} | source={source}]\n{text}")

    context_str = "\n\n".join(formatted)
    user_name = user_memory.get("name", "")
    past_topics = ", ".join(user_memory.get("schemes_asked", []))

    return f"""Language to respond in: {language}
User name: {user_name or "unknown"}
Previously enquired about: {past_topics or "nothing yet"}

--- Knowledge base context ---
{context_str}
--- End context ---

User question: {query}

Use ANY relevant information from the context above to answer. Respond in {language}."""


def _call_gemini(prompt: str) -> str:
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"{SYSTEM_PROMPT}\n\n{prompt}",
        config={"temperature": 0.2, "max_output_tokens": 1024},
    )
    return response.text.strip()


def _call_nemotron(prompt: str) -> str:
    from openai import OpenAI
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    client = OpenAI(base_url=OPENROUTER_BASE, api_key=api_key)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    response = client.chat.completions.create(
        model=FALLBACK_MODEL,
        max_tokens=250,
        temperature=0.2,
        messages=messages,
        extra_headers={"HTTP-Referer": "https://awaaz.ai", "X-Title": "Awaaz"},
        timeout=20,
    )
    return response.choices[0].message.content.strip()


def generate_answer(
    query: str,
    context_chunks: list[dict],
    language: str = "en",
    user_memory: dict | None = None,
) -> str:
    if user_memory is None:
        user_memory = {}

    prompt = _build_prompt(query, context_chunks, language, user_memory)

    # Try Gemini first; fall back to Nemotron on any error
    try:
        raw = _call_gemini(prompt)
        return _extract_answer(raw)
    except Exception as gemini_err:
        try:
            raw = _call_nemotron(prompt)
            return _extract_answer(raw)
        except Exception:
            raise gemini_err


def active_provider() -> str:
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
    if has_gemini:
        return f"gemini/{GEMINI_MODEL} → openrouter/{FALLBACK_MODEL}"
    if has_openrouter:
        return f"openrouter/{FALLBACK_MODEL}"
    return "none"
