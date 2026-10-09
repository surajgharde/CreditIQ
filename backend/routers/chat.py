"""
Multilingual assistant endpoint (English / Hindi / Marathi).

Backed by the OpenAI Chat Completions API. The key is read from the
environment only — never hardcode it here.
"""
import os
import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

Language = Literal["en", "hi", "mr"]

# Canonical name is OPENAI_API_KEY; OPENAI_API is accepted as a legacy alias
# so existing .env files keep working.
def _api_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API") or "").strip()


def _model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


LANG_NAME = {
    "en": "English",
    "hi": "Hindi (हिंदी, Devanagari script)",
    "mr": "Marathi (मराठी, Devanagari script)",
}

# Devanagari is shared by Hindi and Marathi, so script detection alone cannot
# separate them. These are Marathi-specific markers; everything else in
# Devanagari falls through to Hindi.
_MARATHI_MARKERS = (
    "आहे", "आहेत", "नाही", "काय", "कसे", "कशी", "माझ", "तुमच",
    "मला", "कर्जा", "अहवाल", "रक्कम", "व्याज", "का?",
)


def detect_language(text: str) -> Language:
    """Best-effort language guess, used only when the caller sends lang='auto'."""
    has_devanagari = any("ऀ" <= ch <= "ॿ" for ch in text)
    if not has_devanagari:
        return "en"
    lowered = text.lower()
    if any(m in lowered for m in _MARATHI_MARKERS):
        return "mr"
    return "hi"


SYSTEM_PROMPT = """You are the CreditIQ assistant, embedded in a credit-risk and \
fraud-detection platform used by Indian lending analysts.

Scope — you answer questions about:
- how risk scores and probability of default are produced
- what fraud signals mean (GST mismatch, circular trading, related-party flows)
- how to read a Credit Appraisal Memorandum (CAM) or a SHAP explanation
- what documents a borrower needs to submit
- how interest rates relate to assessed risk

Rules:
1. Reply ONLY in {language}. Use that language's native script. Do not mix in \
another language except for established technical terms (GST, SHAP, CAM, PD, \
XGBoost) and numbers.
2. Be concise — two to four sentences unless asked to elaborate.
3. You explain how the platform works. You do NOT make credit decisions, and you \
never state whether a specific borrower should be approved or rejected.
4. If a question falls outside the scope above, say so briefly in {language} and \
redirect to what you can help with.
5. Never invent figures for a specific company. If asked about data you were not \
given, say you do not have it.
6. This platform is a prototype. If asked about regulatory compliance, say it has \
not been certified against any regulatory framework."""


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    lang: Literal["en", "hi", "mr", "auto"] = "en"
    # Prior turns for context; only the most recent few are forwarded.
    history: Optional[List[ChatTurn]] = None


class ChatResponse(BaseModel):
    reply: str
    lang: Language
    model: str


MAX_HISTORY_TURNS = 8


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse, include_in_schema=False)
def chat(req: ChatRequest) -> ChatResponse:
    key = _api_key()
    if not key:
        # 503 rather than 500: the service is fine, it just isn't configured.
        raise HTTPException(
            status_code=503,
            detail=(
                "OPENAI_API_KEY is not set on the server. Add it to backend/.env "
                "(see .env.example) and restart the backend."
            ),
        )

    lang: Language = detect_language(req.message) if req.lang == "auto" else req.lang

    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(language=LANG_NAME[lang])}]
    for turn in (req.history or [])[-MAX_HISTORY_TURNS:]:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": req.message})

    try:
        from openai import OpenAI

        client = OpenAI(api_key=key, timeout=30.0)
        completion = client.chat.completions.create(
            model=_model(),
            messages=messages,
            temperature=0.3,
            max_tokens=500,
        )
        reply = (completion.choices[0].message.content or "").strip()
    except Exception as exc:
        # Log the real cause server-side; keep the client message generic so we
        # do not echo upstream error text (which can carry key fragments).
        logger.exception("Chat completion failed")
        raise HTTPException(
            status_code=502,
            detail=f"Assistant upstream request failed: {type(exc).__name__}",
        )

    if not reply:
        raise HTTPException(status_code=502, detail="Assistant returned an empty reply.")

    return ChatResponse(reply=reply, lang=lang, model=_model())


@router.get("/health")
def chat_health() -> dict:
    """Whether the assistant is configured, without revealing the key."""
    return {
        "configured": bool(_api_key()),
        "model": _model(),
        "languages": ["en", "hi", "mr"],
    }
