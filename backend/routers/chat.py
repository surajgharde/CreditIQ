"""
Multilingual assistant endpoint (English / Hindi / Marathi).

Backed by the Mistral chat completions API, called over REST with requests.
The official SDK is deliberately not used: it is a heavy dependency for one
POST, and its install pulled in packages that clash with ChromaDB's pins here.

The key is read from the environment only — never hardcode it.
"""
import os
import re
import logging
from typing import List, Literal, Optional

import json
import os.path

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.analysis import Analysis
from models.company import Company
from models.fraud import FraudSignal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

Language = Literal["en", "hi", "mr"]

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
REQUEST_TIMEOUT = 30


def _api_key() -> str:
    return (os.getenv("MISTRAL_API_KEY") or "").strip()


def _model() -> str:
    # ministral-8b-latest is the largest model this project's key can reach:
    # mistral-small/medium return a zero request quota and mistral-large a 403.
    # Override with MISTRAL_MODEL on an account with wider access.
    return os.getenv("MISTRAL_MODEL", "ministral-8b-latest")


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
2a. Write plain prose only. No markdown: no **bold**, no bullet lists, no headings, no asterisks. The chat window renders text literally, so markup shows up as stray characters.
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
    # When set, the assistant is grounded in that analysis and answers about
    # that borrower. Without it the assistant can only explain the platform in
    # general — it has no borrower data to work from.
    analysis_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    lang: Language
    model: str
    # Which borrower the answer was grounded in, if any.
    grounded_in: Optional[str] = None


MAX_HISTORY_TURNS = 8

# The chat window renders text literally, so markup arrives as stray characters.
# Asking the model not to emit markdown is not reliable — ministral-8b keeps
# bolding terms regardless — so it is removed here instead.
_MD_PATTERNS = (
    (re.compile(r"\*\*\*(.+?)\*\*\*", re.S), r"\1"),   # ***bold italic***
    (re.compile(r"\*\*(.+?)\*\*", re.S), r"\1"),       # **bold**
    (re.compile(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", re.S), r"\1"),  # *italic*
    (re.compile(r"__(.+?)__", re.S), r"\1"),           # __bold__
    (re.compile(r"`{1,3}([^`]+)`{1,3}", re.S), r"\1"), # `code`
    (re.compile(r"^\s{0,3}#{1,6}\s*", re.M), ""),      # # headings
    (re.compile(r"^\s{0,3}[-*+]\s+", re.M), ""),       # - bullets
    (re.compile(r"^\s{0,3}>\s?", re.M), ""),           # > quotes
)


def strip_markdown(text: str) -> str:
    """Flattens markdown to plain prose for the chat bubble."""
    for pattern, replacement in _MD_PATTERNS:
        text = pattern.sub(replacement, text)
    # Collapse the blank lines left behind by removed list markers.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _money(value) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "not available"
    if num >= 1_00_00_000:
        return f"Rs. {num / 1_00_00_000:.2f} crore"
    if num >= 1_00_000:
        return f"Rs. {num / 1_00_000:.2f} lakh"
    return f"Rs. {num:,.0f}"


def _load_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        logger.warning("Could not read %s for chat context", path)
        return {}


STATEMENT_LABELS = {
    "revenue_fy24": "Revenue from operations",
    "cogs": "Cost of goods sold",
    "gross_profit": "Gross profit",
    "ebitda": "EBITDA",
    "ebit": "EBIT",
    "net_profit": "Net profit after tax",
    "total_assets": "Total assets",
    "total_liabilities": "Total liabilities",
    "total_equity": "Total equity / net worth",
    "total_debt": "Total borrowings",
    "current_assets": "Current assets",
    "current_liabilities": "Current liabilities",
    "cash_equivalents": "Cash and equivalents",
    "interest_expense": "Finance costs",
}

RATIO_LABELS = {
    "current_ratio": "Current ratio",
    "debt_to_equity": "Debt to equity",
    "interest_coverage": "Interest coverage",
    "tol_tnw": "TOL/TNW",
    "ebitda_margin_percent": "EBITDA margin %",
    "gross_profit_margin_percent": "Gross margin %",
    "net_profit_margin_percent": "Net margin %",
}


def build_company_context(db: Session, analysis_id: int, company_id: Optional[int] = None):
    """
    Assembles the facts the assistant may use for one borrower.

    Returns (context_text, company_name), or (None, None) when the analysis does
    not exist or falls outside company_id. The company_id filter is applied in
    SQL so a caller confined to one borrower cannot read another's file by
    passing a different analysis id.
    """
    query = db.query(Analysis).filter(Analysis.id == analysis_id)
    if company_id is not None:
        query = query.filter(Analysis.company_id == company_id)
    analysis = query.first()
    if not analysis:
        return None, None

    company = db.query(Company).filter(Company.id == analysis.company_id).first()
    if not company:
        return None, None

    lines = [
        f"Borrower: {company.company_name}",
        f"CIN: {company.cin_number or 'not on file'}",
        f"GSTIN: {company.gstin_number or 'not on file'}",
        f"Analysis id: {analysis.id}",
        f"Status: {(analysis.analysis_status or 'unknown').upper()}",
        f"Decision: {(analysis.decision or 'not yet decided').upper()}",
        f"Probability of default: {analysis.probability_of_default:.2f}%"
        if analysis.probability_of_default is not None else "Probability of default: not computed",
        f"Facility requested: {_money(company.loan_amount_requested)}",
        f"Facility recommended: {_money(analysis.recommended_loan_amount)}",
        f"Recommended interest rate: {analysis.recommended_interest_rate:.2f}%"
        if analysis.recommended_interest_rate is not None else "Recommended interest rate: not set",
        f"Overall fraud risk: {(analysis.fraud_risk_level or 'not assessed').upper()}",
        f"News risk score: {analysis.news_risk_score:.1f}/100"
        if analysis.news_risk_score is not None else "News risk score: not computed",
        f"Data quality score: {analysis.data_quality_score:.1f}/100"
        if analysis.data_quality_score is not None else "Data quality score: not computed",
    ]

    if (analysis.data_quality_score or 0) <= 0 and analysis.decision:
        lines.append(
            "WARNING: no financial data was extracted for this analysis, so the "
            "decision rests on fallback constants rather than real statements."
        )

    # Extracted statement lines and ratios, written by the OCR step.
    financials = _load_json(f"data/financials_{analysis.id}.json")
    present = [(STATEMENT_LABELS[k], financials[k]) for k in STATEMENT_LABELS if financials.get(k) is not None]
    if present:
        lines.append("")
        lines.append("Extracted financial statement lines:")
        lines += [f"- {label}: {_money(value)}" for label, value in present]
    ratios = [(RATIO_LABELS[k], financials[k]) for k in RATIO_LABELS if financials.get(k) is not None]
    if ratios:
        lines.append("")
        lines.append("Derived ratios:")
        lines += [f"- {label}: {value}" for label, value in ratios]
    missing = [RATIO_LABELS[k] for k in RATIO_LABELS if financials.get(k) is None]
    if missing:
        lines.append(f"Ratios that could not be derived: {', '.join(missing)}.")

    signals = db.query(FraudSignal).filter(FraudSignal.analysis_id == analysis.id).limit(10).all()
    if signals:
        lines.append("")
        lines.append("Fraud signals raised:")
        for sig in signals:
            amount = f", evidence {_money(sig.evidence_amount)}" if sig.evidence_amount else ""
            lines.append(
                f"- {sig.signal_type or 'signal'} ({sig.risk_level or '-'}, "
                f"confidence {sig.confidence_score or '-'}%{amount}): "
                f"{sig.description or 'no description'}"
            )
    else:
        lines.append("")
        lines.append("Fraud signals raised: none.")

    results = _load_json(f"data/results_{analysis.id}.json")
    shap_factors = (results.get("shap") or {}).get("shap_factors") or []
    if shap_factors:
        lines.append("")
        lines.append("Model factor attribution (SHAP), signed contribution to PD:")
        lines += [f"- {f.get('name')}: {f.get('impact')}" for f in shap_factors[:10]]

    news = results.get("news_signals") or []
    if news:
        lines.append("")
        lines.append("Adverse media items:")
        lines += [f"- [{n.get('risk', '-')}] {n.get('signal', 'untitled')}" for n in news[:5]]

    recommendation = results.get("recommendation") or {}
    if recommendation.get("decision_reasoning"):
        lines.append("")
        lines.append(f"Decision reasoning: {recommendation['decision_reasoning']}")
    for condition in (recommendation.get("conditions") or [])[:6]:
        lines.append(f"- Condition: {condition}")

    return "\n".join(lines), company.company_name


GROUNDED_RULES = """

=== BORROWER FILE ===
The facts below are the ONLY source for anything about this borrower. Answer
from them directly, quoting the actual figures.

{context}
=== END BORROWER FILE ===

Additional rules for this conversation:
A. Questions about "this company", "the borrower", "my application", "the
   decision" or similar refer to the borrower above. Answer using its figures.
B. Never state a number that is not in the borrower file. If a figure is absent,
   say it was not captured for this borrower rather than estimating it.
C. Do not discuss any other borrower.
D. Do not invent reasoning either. If the file does not record WHY a figure was
   arrived at — how a recommended amount or rate was derived, what a covenant
   requires — say that the file does not record it. Describing a derivation the
   file does not state is as serious a defect as stating a wrong number.
E. You may explain what a figure means and which pipeline step produced it, but
   you do not overturn or re-decide the assessment."""


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse, include_in_schema=False)
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    _company_scope: Optional[int] = None,
) -> ChatResponse:
    """
    Answers a question, grounded in one borrower's file when analysis_id is set.

    _company_scope is for internal callers (the Telegram bot) that are confined
    to a single company: it is applied as a SQL filter when loading the file, so
    a confined caller cannot reach another borrower by passing its analysis id.
    """
    key = _api_key()
    if not key:
        # 503 rather than 500: the service is fine, it just isn't configured.
        raise HTTPException(
            status_code=503,
            detail=(
                "MISTRAL_API_KEY is not set on the server. Add it to backend/.env "
                "(see .env.example) and restart the backend."
            ),
        )

    lang: Language = detect_language(req.message) if req.lang == "auto" else req.lang

    system_prompt = SYSTEM_PROMPT.format(language=LANG_NAME[lang])
    grounded_in = None
    if req.analysis_id is not None:
        context, grounded_in = build_company_context(db, req.analysis_id, _company_scope)
        if context is None:
            raise HTTPException(
                status_code=404,
                detail=f"No analysis #{req.analysis_id} available to you.",
            )
        system_prompt += GROUNDED_RULES.format(context=context)

    messages = [{"role": "system", "content": system_prompt}]
    for turn in (req.history or [])[-MAX_HISTORY_TURNS:]:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": req.message})

    try:
        response = requests.post(
            MISTRAL_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _model(),
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 500,
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.exception("Mistral request failed")
        raise HTTPException(
            status_code=502,
            detail=f"Assistant upstream request failed: {type(exc).__name__}",
        )

    if response.status_code == 429:
        # Mistral's free tier throttles aggressively; say so plainly rather than
        # reporting a generic upstream failure the user cannot act on.
        raise HTTPException(
            status_code=429,
            detail="The assistant is rate limited right now. Try again in a moment.",
        )

    if response.status_code in (401, 403):
        # Name the cause: a bare "upstream request failed" sent an operator
        # hunting through logs when the answer was simply a rejected key.
        logger.error(
            "Mistral rejected the API key (HTTP %s): %s",
            response.status_code, response.text[:300],
        )
        raise HTTPException(
            status_code=502,
            detail=(
                "The assistant's API key was rejected by Mistral. Check "
                "MISTRAL_API_KEY in backend/.env, then restart the backend — a "
                "running server keeps the key and the provider it started with."
            ),
        )

    if response.status_code >= 400:
        # Log the real body server-side; keep the client message generic so no
        # upstream error text (which can carry key fragments) is echoed back.
        logger.error(
            "Mistral returned %s: %s", response.status_code, response.text[:500]
        )
        raise HTTPException(
            status_code=502,
            detail=f"Assistant upstream request failed (HTTP {response.status_code}).",
        )

    try:
        reply = strip_markdown(response.json()["choices"][0]["message"]["content"] or "")
    except (ValueError, KeyError, IndexError, TypeError):
        logger.error("Unexpected Mistral response shape: %s", response.text[:500])
        raise HTTPException(
            status_code=502, detail="Assistant returned an unreadable response."
        )

    if not reply:
        raise HTTPException(status_code=502, detail="Assistant returned an empty reply.")

    return ChatResponse(reply=reply, lang=lang, model=_model(), grounded_in=grounded_in)


@router.get("/health")
def chat_health() -> dict:
    """Whether the assistant is configured, without revealing the key."""
    return {
        "configured": bool(_api_key()),
        "model": _model(),
        "languages": ["en", "hi", "mr"],
    }
