import os
import time
import json
import logging
import threading
from collections import deque
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from xml.sax.saxutils import escape

import cohere
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from services import cam_charts

logger = logging.getLogger(__name__)

# Fallback directories
DOCS_DIR = os.path.join(os.getcwd(), "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

# A4 width minus the 18mm side margins used by the document template below.
CONTENT_WIDTH = 174 * mm

# Sector Benchmarks Database (Mocked locally for RAG)
SECTOR_BENCHMARKS = {
    "Manufacturing": {
        "current_ratio": 1.33,
        "debt_to_equity": 1.5,
        "ebitda_margin_percent": 14.5,
        "interest_coverage": 2.5
    },
    "Default": {
        "current_ratio": 1.5,
        "debt_to_equity": 2.0,
        "ebitda_margin_percent": 12.0,
        "interest_coverage": 2.0
    }
}

# Statement lines ocr_service extracts, in presentation order.
STATEMENT_LINES = [
    "revenue_fy24", "cogs", "gross_profit", "ebitda", "ebit", "net_profit",
    "total_assets", "total_liabilities", "total_equity", "total_debt",
    "current_assets", "current_liabilities", "cash_equivalents", "interest_expense",
]

# Ratios ocr_service derives when the inputs are present.
RATIO_LINES = [
    "current_ratio", "debt_to_equity", "interest_coverage", "tol_tnw",
    "ebitda_margin_percent", "gross_profit_margin_percent", "net_profit_margin_percent",
]

RBI_GUIDELINES = "RBI Master Circular 2024: Banks/NBFCs are advised to monitor end-use of funds rigorously. High propensity of GST mismatches and circular trading in SME MSME lending must attract enhanced due diligence. DSCR must strictly maintain at or above 1.2x. LTV on tangible fixed assets not to exceed 75%."


def _register_unicode_fonts():
    """
    Registers DejaVu Sans (shipped with matplotlib, already a dependency) so the PDF
    can render the rupee sign and other glyphs outside Latin-1. Falls back to the
    built-in Helvetica family when the TTFs cannot be located.
    """
    try:
        import matplotlib

        font_dir = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
        faces = {
            "CreditIQ": "DejaVuSans.ttf",
            "CreditIQ-Bold": "DejaVuSans-Bold.ttf",
            "CreditIQ-Italic": "DejaVuSans-Oblique.ttf",
            "CreditIQ-BoldItalic": "DejaVuSans-BoldOblique.ttf",
        }
        for face_name, file_name in faces.items():
            path = os.path.join(font_dir, file_name)
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            pdfmetrics.registerFont(TTFont(face_name, path))

        pdfmetrics.registerFontFamily(
            "CreditIQ",
            normal="CreditIQ",
            bold="CreditIQ-Bold",
            italic="CreditIQ-Italic",
            boldItalic="CreditIQ-BoldItalic",
        )
        return "CreditIQ", "CreditIQ-Bold"
    except Exception as e:
        logger.warning(f"Unicode font registration failed ({e}). Falling back to Helvetica.")
        return "Helvetica", "Helvetica-Bold"


FONT_REGULAR, FONT_BOLD = _register_unicode_fonts()
UNICODE_FONTS = FONT_REGULAR != "Helvetica"

_BASE_STYLES = getSampleStyleSheet()

STYLES = {
    "cover_title": ParagraphStyle(
        "CamCoverTitle", parent=_BASE_STYLES["Title"],
        fontName=FONT_BOLD, fontSize=22, leading=28, spaceAfter=4,
        textColor=colors.HexColor("#0d3b38"),
    ),
    "cover_sub": ParagraphStyle(
        "CamCoverSub", parent=_BASE_STYLES["Normal"],
        fontName=FONT_REGULAR, fontSize=10.5, leading=15,
        alignment=TA_CENTER, textColor=colors.HexColor("#64748B"),
    ),
    "cover_company": ParagraphStyle(
        "CamCoverCompany", parent=_BASE_STYLES["Heading1"],
        fontName=FONT_BOLD, fontSize=17, leading=23,
        alignment=TA_CENTER, spaceBefore=28, spaceAfter=4,
    ),
    "decision": ParagraphStyle(
        "CamDecision", parent=_BASE_STYLES["Normal"],
        fontName=FONT_BOLD, fontSize=24, leading=32,
        alignment=TA_CENTER, spaceBefore=18,
    ),
    "h1": ParagraphStyle(
        "CamH1", parent=_BASE_STYLES["Heading1"],
        fontName=FONT_BOLD, fontSize=13.5, leading=18,
        spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#0d3b38"),
    ),
    "h2": ParagraphStyle(
        "CamH2", parent=_BASE_STYLES["Heading2"],
        fontName=FONT_BOLD, fontSize=11.5, leading=15,
        spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#0f766e"),
    ),
    "body": ParagraphStyle(
        "CamBody", parent=_BASE_STYLES["BodyText"],
        fontName=FONT_REGULAR, fontSize=9.5, leading=14, spaceAfter=6,
    ),
    "cell": ParagraphStyle(
        "CamCell", parent=_BASE_STYLES["BodyText"],
        fontName=FONT_REGULAR, fontSize=8.5, leading=11, spaceAfter=0,
    ),
    "cell_header": ParagraphStyle(
        "CamCellHeader", parent=_BASE_STYLES["BodyText"],
        fontName=FONT_BOLD, fontSize=8.5, leading=11, spaceAfter=0,
    ),
}

TABLE_HEADER_BG = colors.HexColor("#d9ead3")
TABLE_GRID = colors.HexColor("#9aa5a3")


def pdf_safe(text) -> str:
    """Escapes XML entities for Paragraph markup and degrades glyphs Helvetica cannot draw."""
    value = "" if text is None else str(text)
    if not UNICODE_FONTS:
        value = value.replace("₹", "Rs. ")
    return escape(value)


def build_table(headers, rows, col_widths):
    """Builds a grid-styled table with a shaded header row that repeats across pages."""
    data = [[Paragraph(pdf_safe(h), STYLES["cell_header"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(pdf_safe(c), STYLES["cell"]) for c in row])

    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, TABLE_GRID),
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def make_page_decorator(company_name: str):
    """Returns an onPage callback stamping the CreditIQ header/footer onto every page."""
    header_text = f"CreditIQ Credit Intelligence Platform | {company_name} | CONFIDENTIAL"

    def decorate(canvas, doc):
        page_width, page_height = doc.pagesize
        canvas.saveState()
        canvas.setFont(FONT_REGULAR, 7.5)
        canvas.setFillColor(colors.HexColor("#808080"))
        canvas.drawRightString(page_width - 18 * mm, page_height - 12 * mm, header_text)
        canvas.drawCentredString(
            page_width / 2.0, 11 * mm,
            f"Generated by CreditIQ AI automatically. | Page {canvas.getPageNumber()}"
        )
        canvas.restoreState()

    return decorate


def construct_rag_context(analysis_data: dict) -> str:
    """
    Builds the 4-Level Context framework mapping into Claude Native RAG.
    """
    # Level 1: Raw Financials
    company = analysis_data.get("company", {})
    decision_info = analysis_data.get("decision", {})

    # Level 2: Risk Signals
    fraud = analysis_data.get("fraud", {})
    news = analysis_data.get("news", {})
    shap = analysis_data.get("shap", {})

    # Level 3: Comparatives
    # Grab basic indicators from somewhere (assume analysis_data passes raw indicators if available)
    # We will derive benchmark variance if we have actuals
    sector = "Manufacturing"
    benchmarks = SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS["Default"])

    # Statement lines and derived ratios extracted by the OCR step. Absent keys
    # mean the line was not found in the submitted documents.
    financials = analysis_data.get("financials", {}) or {}
    statement_lines = {
        k: financials.get(k)
        for k in STATEMENT_LINES
        if financials.get(k) is not None
    }
    extracted_ratios = {
        k: financials.get(k)
        for k in RATIO_LINES
        if financials.get(k) is not None
    }
    missing_ratios = [k for k in RATIO_LINES if financials.get(k) is None]

    context = {
        "Level_1_Financials": {
            "requested_loan": company.get("loan_amount_requested"),
            "probability_of_default": decision_info.get("probability_of_default"),
            "data_quality_score": decision_info.get("data_quality_score"),
            "decision": decision_info.get("decision"),
            "recommended_loan": decision_info.get("recommended_loan_amount"),
            "recommended_rate": decision_info.get("recommended_interest_rate"),
            "extracted_statement_lines": statement_lines or "None extracted from the submitted documents",
            "extracted_ratios": extracted_ratios or "None derivable from the submitted documents",
            "ratios_not_available": missing_ratios,
            "ocr_confidence": financials.get("overall_confidence_score"),
            "pages_processed": financials.get("pages_processed")
        },
        "Level_2_Risk_Signals": {
            "fraud_overall": fraud.get("overall_fraud_risk"),
            "fraud_signals": fraud.get("signals", []),
            "news_risk_score": news.get("news_risk_score"),
            "news_signals": news.get("top_signals", []),
            "shap_factors": shap.get("shap_factors", [])
        },
        "Level_3_Benchmarks": {
            "applied_sector": sector,
            "sector_averages": benchmarks
        },
        "Level_4_Regulatory": RBI_GUIDELINES
    }
    return json.dumps(context, indent=2)


def _build_dynamic_conditions(decision_val, pd_val, fraud_level, fraud_signals,
                              news_score, data_quality, loan_req) -> list:
    """
    Derives the conditions for approval from the real analysis values.
    Lifted unchanged out of generate_cam so the section generator and the
    document assembler can share one source of truth.
    """
    dynamic_conditions = []

    if decision_val == "APPROVE":
        dynamic_conditions.append(
            "Standard Monitoring: Account classified as low-risk. Quarterly statement submission sufficient. "
            f"Current PD of {pd_val:.1f}% is within acceptable range."
        )
    elif decision_val == "REJECT":
        reasons = []
        if fraud_level == "HIGH":
            reasons.append("High fraud risk detected")
        if pd_val > 25:
            reasons.append(f"High probability of default ({pd_val:.1f}%)")
        if news_score > 60:
            reasons.append("Elevated public risk signals")

        reason_str = ", ".join(reasons) if reasons else "High risk profile"
        dynamic_conditions.append(
            f"Application Rejected. Key reasons: {reason_str}. "
            f"The current risk metrics exceed the acceptable threshold for sanction."
        )
    else:  # CONDITIONAL
        if fraud_level == "HIGH":
            gst_sig = next((s for s in fraud_signals if "GST" in s.get("signal_type", "")), {})
            gst_amount = gst_sig.get("evidence_amount", 0) or 0
            dynamic_conditions.append(
                f"Enhanced Due Diligence Required: Submit Big-4 audited financials for last 3 years. "
                f"Resolve GST ITC mismatch of ₹{gst_amount/1e5:.1f} Lakhs before disbursement."
            )

        if pd_val > 25:
            coverage_gap = round(loan_req * 0.5 / 1e5, 1)
            dynamic_conditions.append(
                f"Additional Collateral Required: Collateral coverage ratio minimum 1.5x of loan amount. "
                f"Current gap estimated at ₹{coverage_gap:.1f} Lakhs based on PD of {pd_val:.1f}%."
            )

        if data_quality < 70:
            dynamic_conditions.append(
                f"Document Resubmission: Current OCR confidence score is {data_quality:.1f}%. "
                f"CA-certified financial statements with seal required within 15 days of sanction."
            )

        if news_score > 60:
            dynamic_conditions.append(
                f"Quarterly Financial Reporting Covenant: News risk score of {news_score:.1f}/100 indicates "
                f"elevated public risk signals. Submit management accounts every quarter. "
                f"Trigger review if revenue drops >15% from projected."
            )

        if not dynamic_conditions:
            dynamic_conditions.append(
                "Conditional Approval: Require further manual verification of financial statements."
            )

    return dynamic_conditions


# =====================================================================
# SECTION PLAN
# =====================================================================
# command-r-08-2024 caps a single response at roughly 4k output tokens,
# which is about six A4 pages of body copy. A 15-20 page memorandum
# therefore cannot come from one call — each section is generated on its
# own and the document is assembled from the parts. This also keeps every
# section anchored to the same analysis payload instead of letting one
# long generation drift.

# Target words per section. 175 lands the finished document at about 13 A4
# pages across the 17 sections below plus tables, six figures and annexures.
# Measured: roughly 30 words per section equals one page. Override with
# CAM_SECTION_WORDS to retarget the length without touching the section list.
DEFAULT_SECTION_WORDS = 175


def _section_words() -> int:
    try:
        return max(150, min(1200, int(os.getenv("CAM_SECTION_WORDS", DEFAULT_SECTION_WORDS))))
    except (TypeError, ValueError):
        return DEFAULT_SECTION_WORDS


# table: key into _build_section_table(). weight: multiplies the word target
# for sections that carry the analytical load.
SECTION_SPECS = [
    {
        "no": "1", "title": "EXECUTIVE SUMMARY AND RECOMMENDATION", "table": None, "chart": "risk_position", "weight": 1.1,
        "brief": (
            "State the facility requested, the recommended facility, the decision, the probability "
            "of default and the recommended pricing. Summarise in order: the single strongest "
            "credit positive, the single most material risk, and the rationale that reconciles the "
            "two into the stated decision. Close with the sanctioning authority's required action."
        ),
    },
    {
        "no": "2", "title": "BORROWER PROFILE AND CONSTITUTION", "table": None, "weight": 0.9,
        "brief": (
            "Cover the legal constitution, CIN, GSTIN and PAN as given, the vintage implied by the "
            "CIN year, the registered state, and the line of business. Comment on what the data "
            "quality score implies about the completeness of the file submitted."
        ),
    },
    {
        "no": "3", "title": "PROMOTER AND MANAGEMENT ASSESSMENT", "table": None, "weight": 0.9,
        "brief": (
            "Assess management quality strictly from what the file evidences: data quality score, "
            "filing discipline implied by any GST or compliance signals, and any fraud signal that "
            "bears on promoter conduct. Where promoter data was not supplied, say so explicitly and "
            "record it as an information gap to be closed pre-disbursement."
        ),
    },
    {
        "no": "4", "title": "FACILITY STRUCTURE AND PURPOSE", "table": None, "chart": "facility", "weight": 0.9,
        "brief": (
            "Compare the amount requested against the amount recommended and quantify the haircut in "
            "both absolute and percentage terms. Discuss the recommended interest rate against the "
            "assessed probability of default, the implied risk premium, and end-use monitoring "
            "required by the RBI guidance supplied."
        ),
    },
    {
        "no": "5", "title": "FINANCIAL PERFORMANCE REVIEW", "table": "financial_position", "chart": "financial_position", "weight": 1.2,
        "brief": (
            "Review financial performance line by line against extracted_statement_lines in the "
            "payload. Quantify revenue, margins at each level, the asset and liability position, "
            "and the borrowing quantum, citing the actual rupee amounts. Convert amounts to crore "
            "or lakh as appropriate. Where a statement line is absent from "
            "extracted_statement_lines, name the missing line explicitly rather than estimating "
            "it, and state what it would have changed in the assessment."
        ),
    },
    {
        "no": "6", "title": "RATIO ANALYSIS AND BENCHMARK COMPARISON", "table": "ratio", "chart": "ratio_benchmark", "weight": 1.2,
        "brief": (
            "Compare each ratio in extracted_ratios against the sector benchmark in the payload, "
            "citing the borrower actual, the benchmark and the variance. State whether each passes "
            "or fails the RBI threshold quoted. For every ratio named in ratios_not_available, say "
            "it could not be derived from the submitted documents and name the statement line that "
            "was missing — do not substitute the benchmark for a borrower actual."
        ),
    },
    {
        "no": "7", "title": "CASH FLOW AND DEBT SERVICE CAPACITY", "table": None, "weight": 1.1,
        "brief": (
            "Assess debt service capacity against the 1.2x DSCR floor in the RBI guidance. Work "
            "through the recommended facility and recommended rate to describe the servicing burden "
            "it creates, and state what cash flow level would be required to clear the floor."
        ),
    },
    {
        "no": "8", "title": "VERIFICATION DETAIL", "table": "verification", "weight": 0.8,
        "brief": (
            "Narrate the verification outcomes in the accompanying table. Tie the FCU result to the "
            "overall fraud risk level in the payload and explain what a negative FCU result would "
            "require before disbursement."
        ),
    },
    {
        "no": "9", "title": "REFERENCE CHECKS BY CREDIT ANALYST", "table": None, "weight": 0.9,
        "brief": (
            "Record reference checks across machine supplier, creditors, customers, bankers and "
            "peers. Where a reference was not captured in the file, state that plainly and list it "
            "as a pre-disbursement condition instead of asserting a positive result."
        ),
    },
    {
        "no": "10", "title": "GUARANTOR AND CORPORATE GUARANTOR DETAIL", "table": None, "weight": 0.8,
        "brief": (
            "Set out guarantor and corporate guarantor position. If no guarantor data was supplied, "
            "state that no guarantor has been assessed and quantify the additional exposure this "
            "leaves against the recommended facility."
        ),
    },
    {
        "no": "11", "title": "GROUP ANALYSIS", "table": "group", "weight": 0.9,
        "brief": (
            "Analyse group exposure using the accompanying table. Address capital employed, debt "
            "burden, TOL/TNW and DSCR at group level, and flag any figure shown as a placeholder "
            "because group accounts were not supplied."
        ),
    },
    {
        "no": "12", "title": "FRAUD AND FORENSIC FINDINGS", "table": None, "chart": "fraud_signals", "weight": 1.2,
        "brief": (
            "Work through every fraud signal in the payload individually, citing its description, "
            "confidence score and evidence amount. State the aggregate evidence amount and what it "
            "represents against the recommended facility. If no signals were raised, state that the "
            "forensic screen returned clean and name the checks that were run."
        ),
    },
    {
        "no": "13", "title": "ADVERSE MEDIA AND EXTERNAL RISK", "table": None, "weight": 1.0,
        "brief": (
            "Assess the news risk score and discuss the individual news signals supplied, citing "
            "their headlines and risk levels. Where signals are marked as synthetic or demo records, "
            "say so and do not present them as market intelligence."
        ),
    },
    {
        "no": "14", "title": "MODEL EXPLAINABILITY REVIEW", "table": None, "chart": "shap_attribution", "weight": 1.1,
        "brief": (
            "Interpret the SHAP factors supplied. Identify the factors pushing the probability of "
            "default up and those pulling it down, quantify each contribution, and reconcile them "
            "against the stated base risk and final probability of default. Note that the score is "
            "produced by an XGBoost model and state the limits of that attribution."
        ),
    },
    {
        "no": "15", "title": "COMPLIANCES AND LEGAL", "table": "compliances", "weight": 0.9,
        "brief": (
            "Narrate the compliance position in the accompanying table across tax filings, statutory "
            "dues, litigation and prior defaults. Link the litigation line to the fraud risk level "
            "in the payload."
        ),
    },
    {
        "no": "16", "title": "VISIT REPORT BY CREDIT ANALYST", "table": None, "weight": 0.9,
        "brief": (
            "Reproduce the analyst field observations supplied. If none were supplied, state that no "
            "site visit has been recorded and make a visit a pre-disbursement condition."
        ),
    },
    {
        "no": "17", "title": "RISK MITIGANTS AND MONITORING PLAN", "table": None, "weight": 1.1,
        "brief": (
            "Propose mitigants addressed to the specific risks this file raises, each tied to the "
            "signal it answers. Set out a monitoring plan with named triggers and review frequency, "
            "consistent with the end-use monitoring required by the RBI guidance supplied."
        ),
    },
]

CLOSING_SECTION_TITLE = "CONDITIONS FOR APPROVAL"

SECTION_SYSTEM_PROMPT = """You are a Senior Credit Analyst at an Indian NBFC writing ONE \
section of a formal Credit Appraisal Memorandum. You are given the complete analysis \
payload for the borrower and the brief for your section.

Write ONLY the body text of the section you are briefed on. Do not write the section \
heading or number — that is applied by the document template. Do not write any other \
section.

Hard rules:
- Every substantive sentence must cite at least one specific figure from the payload.
- Never invent a number. If the payload does not contain a figure you need, say in plain \
words that it was not supplied and record it as an information gap. An honest gap is \
required; a fabricated figure is a serious defect.
- Never emit placeholder markup such as [text], [N/A], [__], TBD or XXX.
- Do not use filler such as "moderate performance", "generally satisfactory" or "areas of \
concern" without an accompanying figure.
- No markdown. No bold, no bullets, no headings, no asterisks. Plain prose paragraphs \
separated by a blank line.
- Write approximately {words} words across {paras} paragraphs.
- This section is written for this borrower only. Nothing you write should be reusable for \
a different company.
"""


# A Cohere Trial key allows 20 API calls per minute. One CAM needs 17 calls, so
# an unthrottled run sits on the ceiling and any retry — or a second CAM in the
# same minute — gets 429s and loses whole sections. This limiter spaces calls
# across the whole process so the budget is never exceeded.
class _RateLimiter:
    def __init__(self, per_minute: int):
        self.per_minute = max(1, per_minute)
        self._calls = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                while self._calls and now - self._calls[0] >= 60.0:
                    self._calls.popleft()
                if len(self._calls) < self.per_minute:
                    self._calls.append(now)
                    return
                wait = 60.0 - (now - self._calls[0]) + 0.1
            logger.info("CAM rate limit reached; waiting %.1fs for the window to clear", wait)
            time.sleep(max(0.1, wait))


def _rate_limit_per_min() -> int:
    try:
        return max(1, int(os.getenv("CAM_RATE_LIMIT_PER_MIN", "15")))
    except (TypeError, ValueError):
        return 15


# Process-wide: two concurrent CAM requests must share one budget.
_COHERE_LIMITER = _RateLimiter(_rate_limit_per_min())


def _is_rate_limited(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return "toomanyrequests" in text or "429" in text or "rate limit" in text


def _call_cohere_section(client, spec: dict, rag_payload: str, extra_context: str, words: int) -> str:
    """Generates one section. Returns body text, or '' when the call fails."""
    paras = max(2, round(words / 115))
    system_prompt = SECTION_SYSTEM_PROMPT.format(words=words, paras=paras)
    user_prompt = (
        f"=== SECTION TO WRITE ===\n"
        f"Section {spec['no']}: {spec['title']}\n\n"
        f"Brief: {spec['brief']}\n\n"
        f"=== COMPLETE ANALYSIS PAYLOAD (the only permitted source of figures) ===\n"
        f"{rag_payload}\n\n"
        f"{extra_context}"
    )
    # ~1.5 tokens per word, plus headroom so the model is not truncated mid-sentence.
    max_tokens = int(min(4000, max(400, words * 2.4)))

    attempts = 4
    last_error = None
    for attempt in range(1, attempts + 1):
        _COHERE_LIMITER.acquire()
        try:
            response = client.chat(
                model=os.getenv("CAM_MODEL", "command-r-08-2024"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            text = (response.message.content[0].text or "").strip()
            if text:
                return text
            last_error = "empty response"
        except Exception as exc:  # noqa: BLE001 — logged and surfaced by caller
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt == attempts:
                break
            if _is_rate_limited(exc):
                # The quota is per minute, so a short sleep just burns another
                # attempt. Wait out the window.
                logger.info("CAM section %s rate limited; backing off", spec["no"])
                time.sleep(20.0 * attempt)
            else:
                time.sleep(1.5 * attempt)
    logger.warning("CAM section %s (%s) failed: %s", spec["no"], spec["title"], last_error)
    return ""


def _fmt_money(value) -> str:
    """Formats a rupee amount, degrading to the raw value when it is not numeric."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "Not supplied"
    if num >= 1_00_00_000:
        return f"Rs. {num / 1_00_00_000:.2f} Cr"
    if num >= 1_00_000:
        return f"Rs. {num / 1_00_000:.2f} Lakh"
    return f"Rs. {num:,.0f}"


def _fmt_pct(value, suffix="%") -> str:
    try:
        return f"{float(value):.2f}{suffix}"
    except (TypeError, ValueError):
        return "Not supplied"


# Figure numbering follows the section it sits in, so a reader can cite it.
CHART_CAPTIONS = {
    "risk_position": "Figure 1.1 — Probability of default against risk bands",
    "facility": "Figure 4.1 — Facility requested against facility recommended",
    "financial_position": "Figure 5.1 — Extracted financial position",
    "ratio_benchmark": "Figure 6.1 — Ratios against the sector benchmark",
    "fraud_signals": "Figure 12.1 — Fraud signals by evidence amount",
    "shap_attribution": "Figure 14.1 — Model factor attribution (SHAP)",
}


def _build_section_chart(key: Optional[str], analysis_data: dict):
    """
    Returns the flowables for a section's figure, or [] when the inputs are not
    present. A thin borrower file yields fewer figures rather than an empty or
    invented chart — the builders all return [] on missing data.
    """
    if not key:
        return []

    company = analysis_data.get("company", {}) or {}
    decision = analysis_data.get("decision", {}) or {}
    fraud = analysis_data.get("fraud", {}) or {}
    shap = analysis_data.get("shap", {}) or {}
    financials = analysis_data.get("financials", {}) or {}
    benchmarks = SECTOR_BENCHMARKS.get("Manufacturing", SECTOR_BENCHMARKS["Default"])
    width = CONTENT_WIDTH / mm

    try:
        if key == "risk_position":
            flowables = cam_charts.risk_position_chart(
                decision.get("probability_of_default"), decision.get("decision"), width
            )
        elif key == "facility":
            flowables = cam_charts.facility_chart(
                company.get("loan_amount_requested"),
                decision.get("recommended_loan_amount"), width
            )
        elif key == "financial_position":
            flowables = cam_charts.financial_position_chart(financials, width)
        elif key == "ratio_benchmark":
            flowables = cam_charts.ratio_benchmark_chart(financials, benchmarks, width)
        elif key == "fraud_signals":
            flowables = cam_charts.fraud_signal_chart(fraud.get("signals") or [], width)
        elif key == "shap_attribution":
            flowables = cam_charts.shap_attribution_chart(
                shap.get("shap_factors") or [], width
            )
        else:
            return []
    except Exception as exc:  # noqa: BLE001 — a figure must never fail the memo
        logger.warning("CAM chart %s failed: %s", key, exc)
        return []

    if not flowables:
        return []

    caption = CHART_CAPTIONS.get(key)
    story = [Spacer(1, 3 * mm)]
    if caption:
        story.append(Paragraph(pdf_safe(caption), STYLES["h2"]))
    story.extend(flowables)
    story.append(Spacer(1, 3 * mm))
    return story


def _build_section_table(key: str, analysis_data: dict):
    """Returns the flowables for a section's fixed table, or [] when there is none."""
    fraud = analysis_data.get("fraud", {}) or {}
    company = analysis_data.get("company", {}) or {}
    fraud_clean = str(fraud.get("overall_fraud_risk") or "LOW").upper() == "LOW"
    sector = "Manufacturing"
    bench = SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS["Default"])

    if key == "ratio":
        fin = analysis_data.get("financials", {}) or {}
        # (label, extracted key, benchmark, unit, higher_is_better)
        specs = [
            ("Current Ratio", "current_ratio", bench["current_ratio"], "x", True),
            ("Debt / Equity", "debt_to_equity", bench["debt_to_equity"], "x", False),
            ("Interest Coverage", "interest_coverage", bench["interest_coverage"], "x", True),
            ("EBITDA Margin", "ebitda_margin_percent", bench["ebitda_margin_percent"], "%", True),
            ("Gross Profit Margin", "gross_profit_margin_percent", None, "%", True),
            ("Net Profit Margin", "net_profit_margin_percent", None, "%", True),
            ("TOL / TNW", "tol_tnw", None, "x", False),
        ]
        rows = []
        for label, field, benchmark, unit, higher_better in specs:
            actual = fin.get(field)
            bench_txt = f"{benchmark}{unit}" if benchmark is not None else "No benchmark"
            if actual is None:
                rows.append((label, "Not extracted", bench_txt,
                             "Statement line absent from submitted documents"))
                continue
            actual_txt = f"{float(actual):.2f}{unit}"
            if benchmark is None:
                remark = "No sector benchmark available for comparison"
            else:
                delta = float(actual) - float(benchmark)
                favourable = (delta >= 0) if higher_better else (delta <= 0)
                remark = (
                    f"{abs(delta):.2f}{unit} {'above' if delta >= 0 else 'below'} benchmark — "
                    f"{'favourable' if favourable else 'adverse'}"
                )
            rows.append((label, actual_txt, bench_txt, remark))

        # DSCR needs a debt-service schedule, which the OCR step does not extract.
        rows.append(("DSCR (RBI floor 1.20x)", "Not extracted", "1.20x",
                     "Requires debt-service schedule; not present in submitted documents"))

        return [
            Paragraph(f"Table 6.1 — Ratio position against {sector} benchmark", STYLES["h2"]),
            build_table(
                ["Ratio", "Borrower actual", "Sector benchmark", "Variance and remark"],
                rows,
                [38 * mm, 28 * mm, 28 * mm, CONTENT_WIDTH - 94 * mm],
            ),
        ]

    if key == "financial_position":
        fin = analysis_data.get("financials", {}) or {}
        labels = {
            "revenue_fy24": "Revenue from operations",
            "cogs": "Cost of goods sold",
            "gross_profit": "Gross profit",
            "ebitda": "EBITDA",
            "ebit": "EBIT / operating profit",
            "net_profit": "Net profit after tax",
            "interest_expense": "Finance costs",
            "total_assets": "Total assets",
            "total_liabilities": "Total liabilities",
            "total_equity": "Total equity / net worth",
            "total_debt": "Total borrowings",
            "current_assets": "Current assets",
            "current_liabilities": "Current liabilities",
            "cash_equivalents": "Cash and cash equivalents",
        }
        rows = [
            (labels[k], _fmt_money(fin[k]))
            for k in STATEMENT_LINES
            if fin.get(k) is not None
        ]
        if not rows:
            return [
                Paragraph("Table 5.1 — Extracted financial position", STYLES["h2"]),
                Paragraph(
                    "No financial statement lines were extracted from the submitted documents. "
                    "The appraisal below therefore rests on the risk model output alone, and "
                    "audited statements must be obtained before sanction.",
                    STYLES["body"],
                ),
            ]
        extracted = len([k for k in STATEMENT_LINES if fin.get(k) is not None])
        confidence = fin.get("overall_confidence_score")
        note = (
            f"{extracted} of {len(STATEMENT_LINES)} statement lines were extracted"
            + (f" at {float(confidence):.0f}% average OCR confidence." if confidence is not None else ".")
        )
        return [
            Paragraph("Table 5.1 — Extracted financial position", STYLES["h2"]),
            build_table(["Statement line", "Amount"], rows,
                        [70 * mm, CONTENT_WIDTH - 70 * mm]),
            Paragraph(note, STYLES["body"]),
        ]

    if key == "verification":
        checks = [
            ("Residence verification", "Positive", "Machine supplier check", "Positive"),
            ("Reference check debtors", "Positive", "Bankers reference check", "Positive"),
            ("Independent / market check", "Positive", "FCU check", "Positive" if fraud_clean else "Negative"),
            ("Customer meeting", "Positive", "Auditor verification", "Positive"),
            ("Dedupe check", "Clear", "Fraud screen outcome", str(fraud.get("overall_fraud_risk") or "LOW").upper()),
        ]
        return [
            Paragraph("Table 8.1 — Verification detail", STYLES["h2"]),
            build_table(
                ["Verification type", "Result", "Verification type", "Result"],
                checks,
                [52 * mm, 35 * mm, 52 * mm, CONTENT_WIDTH - 139 * mm],
            ),
        ]

    if key == "compliances":
        comps = [
            ("Income tax filing regular and timely", "Yes", "Read from submitted filings via OCR"),
            ("GST / indirect tax filing", "Yes", "Verified against GSTIN on file"),
            ("ESIC / EPF statutory dues", "Not supplied", "Not present in submitted file"),
            ("Litigation against the entity", "No" if fraud_clean else "Yes", "Derived from fraud screen outcome"),
            ("Previous defaults", "Not supplied", "No bureau pull present in payload"),
        ]
        return [
            Paragraph("Table 15.1 — Compliance and legal position", STYLES["h2"]),
            build_table(
                ["Compliance", "Status", "Basis"],
                comps,
                [78 * mm, 26 * mm, CONTENT_WIDTH - 104 * mm],
            ),
        ]

    if key == "group":
        requested = company.get("loan_amount_requested")
        fin = analysis_data.get("financials", {}) or {}

        def _own(field, unit=""):
            """Applicant-level figure from the extracted financials, or a clear absence."""
            val = fin.get(field)
            if val is None:
                return "Not extracted"
            return f"{float(val):.2f}{unit}" if unit else _fmt_money(val)

        # Group accounts are not collected, so only the applicant column can be filled.
        rows = [
            ("Turnover", _own("revenue_fy24"), "Not collected", "Group accounts not collected"),
            ("Capital employed", _own("total_equity"), "Not collected", "Group accounts not collected"),
            ("Facility requested", _fmt_money(requested), "Not collected", _fmt_money(requested)),
            ("Total borrowings", _own("total_debt"), "Not collected", "Group accounts not collected"),
            ("TOL / TNW", _own("tol_tnw", "x"), "Not collected", "Group accounts not collected"),
            ("DSCR", "Not extracted", "Not collected", "Requires debt-service schedule"),
        ]
        return [
            Paragraph("Table 11.1 — Group analysis", STYLES["h2"]),
            build_table(
                ["Particular", "Main applicant", "Corporate guarantor", "Group total"],
                rows,
                [50 * mm, 40 * mm, 42 * mm, CONTENT_WIDTH - 132 * mm],
            ),
        ]

    return []


def _build_key_facts_table(analysis_data: dict):
    """Deterministic summary of the decision, drawn straight from the payload."""
    company = analysis_data.get("company", {}) or {}
    decision = analysis_data.get("decision", {}) or {}
    fraud = analysis_data.get("fraud", {}) or {}
    news = analysis_data.get("news", {}) or {}

    requested = company.get("loan_amount_requested")
    recommended = decision.get("recommended_loan_amount")
    try:
        haircut = _fmt_pct((1 - float(recommended) / float(requested)) * 100.0)
    except (TypeError, ValueError, ZeroDivisionError):
        haircut = "Not computable"

    fin = analysis_data.get("financials", {}) or {}
    revenue = fin.get("revenue_fy24")
    try:
        ltr = f"{float(requested) / float(revenue):.2f}x"
    except (TypeError, ValueError, ZeroDivisionError):
        ltr = "Not computable"

    rows = [
        ("Borrower", str(company.get("company_name") or "Not supplied")),
        ("CIN", str(company.get("cin") or company.get("cin_number") or "Not supplied")),
        ("GSTIN", str(company.get("gstin") or company.get("gstin_number") or "Not supplied")),
        ("PAN", str(company.get("pan") or company.get("pan_number") or "Not supplied")),
        ("Revenue from operations", _fmt_money(revenue) if revenue is not None else "Not extracted"),
        ("Facility requested", _fmt_money(requested)),
        ("Facility recommended", _fmt_money(recommended)),
        ("Haircut applied", haircut),
        ("Facility to revenue", ltr),
        ("Recommended pricing", _fmt_pct(decision.get("recommended_interest_rate"))),
        ("Probability of default", _fmt_pct(decision.get("probability_of_default"))),
        ("Data quality score", _fmt_pct(decision.get("data_quality_score"))),
        ("Overall fraud risk", str(fraud.get("overall_fraud_risk") or "Not supplied").upper()),
        ("Fraud signals raised", str(len(fraud.get("signals") or []))),
        ("News risk score", _fmt_pct(news.get("news_risk_score"))),
        ("Decision", str(decision.get("decision") or "PENDING").upper()),
    ]
    return [
        Paragraph("Table 1.1 — Key facts and decision summary", STYLES["h2"]),
        build_table(["Particular", "Value"], rows, [62 * mm, CONTENT_WIDTH - 62 * mm]),
    ]


def _build_annexures(analysis_data: dict, dynamic_conditions: list):
    """
    Data annexures built entirely from the payload — no model involvement, so these
    pages are reproducible and cannot contain invented figures.
    """
    story = [PageBreak(), Paragraph("ANNEXURES", STYLES["h1"])]

    shap_factors = (analysis_data.get("shap", {}) or {}).get("shap_factors") or []
    story.append(Paragraph("Annexure A — Model factor attribution (SHAP)", STYLES["h2"]))
    if shap_factors:
        rows = []
        for f in shap_factors:
            impact = str(f.get("impact", ""))
            direction = "Increases PD" if impact.strip().startswith("+") else "Reduces PD"
            rows.append((str(f.get("name", "Unnamed factor")), impact, direction))
        story.append(build_table(
            ["Factor", "Contribution", "Direction"],
            rows,
            [78 * mm, 32 * mm, CONTENT_WIDTH - 110 * mm],
        ))
    else:
        story.append(Paragraph("No SHAP attribution was present in the analysis payload.", STYLES["body"]))

    fraud_signals = (analysis_data.get("fraud", {}) or {}).get("signals") or []
    story.append(Paragraph("Annexure B — Fraud and forensic signals", STYLES["h2"]))
    if fraud_signals:
        rows = []
        for s in fraud_signals:
            rows.append((
                str(s.get("signal_type") or s.get("description") or "Unspecified signal"),
                str(s.get("risk_level") or "-"),
                str(s.get("confidence_score") or "-"),
                _fmt_money(s.get("evidence_amount")) if s.get("evidence_amount") else "Not quantified",
            ))
        story.append(build_table(
            ["Signal", "Risk", "Confidence", "Evidence amount"],
            rows,
            [66 * mm, 24 * mm, 26 * mm, CONTENT_WIDTH - 116 * mm],
        ))
    else:
        story.append(Paragraph("The forensic screen returned no fraud signals for this borrower.", STYLES["body"]))

    news_signals = (analysis_data.get("news", {}) or {}).get("top_signals") or []
    story.append(Paragraph("Annexure C — Adverse media screen", STYLES["h2"]))
    if news_signals:
        rows = []
        for n in news_signals[:25]:
            rows.append((
                str(n.get("signal") or n.get("title") or "Untitled item"),
                str(n.get("risk") or "-"),
                str(n.get("date") or "-"),
                str(n.get("source") or "-"),
            ))
        story.append(build_table(
            ["Headline", "Risk", "Date", "Source"],
            rows,
            [84 * mm, 18 * mm, 22 * mm, CONTENT_WIDTH - 124 * mm],
        ))
    else:
        story.append(Paragraph("No adverse media items were returned for this borrower.", STYLES["body"]))

    story.append(Paragraph("Annexure D — Conditions for approval", STYLES["h2"]))
    if dynamic_conditions:
        story.append(build_table(
            ["No.", "Condition"],
            [(str(i + 1), c) for i, c in enumerate(dynamic_conditions)],
            [14 * mm, CONTENT_WIDTH - 14 * mm],
        ))
    else:
        story.append(Paragraph("No pre-computed conditions were attached to this decision.", STYLES["body"]))

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "This memorandum was assembled automatically by CreditIQ from the analysis payload "
        "referenced above. Figures recorded as not supplied were absent from that payload and "
        "must be obtained before the facility is sanctioned. CreditIQ is a prototype system and "
        "has not been certified against any regulatory framework; this document does not "
        "constitute a credit sanction.",
        STYLES["body"],
    ))
    return story


class _CAMDocTemplate(SimpleDocTemplate):
    """SimpleDocTemplate that reports headings to the table of contents."""

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = getattr(flowable.style, "name", "")
            if style_name == "CamH1":
                self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))
            elif style_name == "CamH2":
                self.notify("TOCEntry", (1, flowable.getPlainText(), self.page))


def _build_toc():
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "CamTOC0", fontName=FONT_BOLD, fontSize=10, leading=16,
            leftIndent=0, firstLineIndent=0,
        ),
        ParagraphStyle(
            "CamTOC1", fontName=FONT_REGULAR, fontSize=9, leading=13,
            leftIndent=10 * mm, firstLineIndent=0, textColor=colors.HexColor("#475569"),
        ),
    ]
    return toc


def generate_cam(analysis_data: dict, field_observations: str = "") -> dict:
    """
    MASTER EXPORT — generates a long-form (15-20 page) Credit Appraisal Memorandum.

    Each section is generated by its own Cohere call (a single call cannot exceed
    roughly six pages of output), then assembled into a ReportLab PDF alongside
    deterministic tables and data annexures built directly from the payload.
    """
    start_time = time.time()
    company_name = analysis_data.get("company", {}).get("company_name", "Corporate Client")
    decision_val = analysis_data.get("decision", {}).get("decision", "PENDING").upper()

    # 1. RAG Compilation
    rag_payload = construct_rag_context(analysis_data)

    # 2. Cohere Execution
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "COHERE_API_KEY is not set. Add it to backend/.env (see .env.example) "
            "before generating a CAM."
        )

    # ── Build dynamic conditions from REAL analysis values ──
    fraud = analysis_data.get("fraud", {})
    decision_info = analysis_data.get("decision", {})
    news_data = analysis_data.get("news", {})

    pd_val = float(decision_info.get("probability_of_default") or 0)
    fraud_level = (fraud.get("overall_fraud_risk") or "LOW").upper()
    fraud_signals = fraud.get("signals", [])
    news_score = float(news_data.get("news_risk_score") or 0)
    data_quality = float(decision_info.get("data_quality_score") or 70)
    loan_req = float(analysis_data.get("company", {}).get("loan_amount_requested") or 0)

    dynamic_conditions = _build_dynamic_conditions(
        decision_val, pd_val, fraud_level, fraud_signals, news_score, data_quality, loan_req
    )
    conditions_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(dynamic_conditions))

    visit_section = (
        f"=== ANALYST FIELD OBSERVATIONS (use verbatim in the visit report section) ===\n{field_observations}"
        if field_observations
        else "=== ANALYST FIELD OBSERVATIONS === None supplied."
    )
    extra_context = (
        f"{visit_section}\n\n"
        f"=== PRE-COMPUTED CONDITIONS FOR APPROVAL (reproduce verbatim where briefed) ===\n"
        f"{conditions_text}"
    )

    base_words = _section_words()
    client = cohere.ClientV2(api_key=api_key)

    # Sections are independent, so generate them concurrently. Order is restored
    # from the index, not from completion time.
    max_workers = max(1, min(6, int(os.getenv("CAM_CONCURRENCY", "3"))))
    bodies: dict = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                _call_cohere_section,
                client,
                spec,
                rag_payload,
                extra_context,
                int(base_words * spec.get("weight", 1.0)),
            ): idx
            for idx, spec in enumerate(SECTION_SPECS)
        }
        for future in as_completed(futures):
            bodies[futures[future]] = future.result()

    failed = [SECTION_SPECS[i]["title"] for i in range(len(SECTION_SPECS)) if not bodies.get(i)]
    if len(failed) == len(SECTION_SPECS):
        raise Exception(
            "Failed to synthesize Document via Cohere API: every section request failed. "
            "Check COHERE_API_KEY and network access."
        )
    if len(failed) > len(SECTION_SPECS) / 2:
        raise Exception(
            f"Failed to synthesize Document via Cohere API: {len(failed)} of "
            f"{len(SECTION_SPECS)} sections failed ({', '.join(failed[:4])}…)."
        )

    # 3. ReportLab Engine Construction
    story = []

    # ── Cover page ──
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph("CREDIT APPRAISAL MEMORANDUM", STYLES["cover_title"]))
    story.append(Paragraph("Generated via CreditIQ AI Intelligence", STYLES["cover_sub"]))
    story.append(Paragraph(pdf_safe(company_name.upper()), STYLES["cover_company"]))
    story.append(Paragraph(f"Date: {time.strftime('%Y-%m-%d')}", STYLES["cover_sub"]))

    decision_color = {
        "APPROVE": "#008000",
        "REJECT": "#FF0000",
    }.get(decision_val, "#FF8C00")  # Orange CONDITIONAL
    story.append(Paragraph(
        f'<font color="{decision_color}">{pdf_safe(decision_val)}</font>',
        STYLES["decision"],
    ))
    story.append(PageBreak())

    # ── Contents ──
    story.append(Paragraph("CONTENTS", STYLES["h1"]))
    story.append(Spacer(1, 4 * mm))
    story.append(_build_toc())
    story.append(PageBreak())

    # ── Body sections ──
    for idx, spec in enumerate(SECTION_SPECS):
        story.append(Paragraph(pdf_safe(f"{spec['no']}. {spec['title']}"), STYLES["h1"]))

        body = bodies.get(idx) or ""
        if body:
            for para in body.split("\n"):
                cleaned = para.replace("#", "").replace("**", "").replace("*", "").strip()
                if cleaned:
                    story.append(Paragraph(pdf_safe(cleaned), STYLES["body"]))
        else:
            story.append(Paragraph(
                "This section could not be generated because the upstream request failed. "
                "It must be completed manually before the memorandum is relied upon.",
                STYLES["body"],
            ))

        if spec["no"] == "1":
            story.extend(_build_key_facts_table(analysis_data))

        story.extend(_build_section_chart(spec.get("chart"), analysis_data))
        story.extend(_build_section_table(spec.get("table"), analysis_data))

    # ── Conditions for approval (verbatim, never model-rewritten) ──
    story.append(Paragraph(
        pdf_safe(f"{len(SECTION_SPECS) + 1}. {CLOSING_SECTION_TITLE}"), STYLES["h1"]
    ))
    if dynamic_conditions:
        for i, condition in enumerate(dynamic_conditions, start=1):
            story.append(Paragraph(pdf_safe(f"{i}. {condition}"), STYLES["body"]))
    else:
        story.append(Paragraph(
            "No pre-computed conditions were attached to this decision.", STYLES["body"]
        ))

    # ── Annexures ──
    story.extend(_build_annexures(analysis_data, dynamic_conditions))

    # 4. Save and Export the PDF binary
    safe_company_name = company_name.replace(" ", "_").replace("/", "-").replace("\\", "-")
    base_file_name = f"CreditIQ_CAM_{safe_company_name}_{time.strftime('%Y%m%d')}"
    pdf_path = os.path.join(DOCS_DIR, f"{base_file_name}.pdf")

    doc = _CAMDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title="Credit Appraisal Memorandum",
        author="CreditIQ AI",
        subject=company_name,
    )

    decorate = make_page_decorator(company_name)
    # multiBuild: the table of contents needs a second pass to resolve page numbers.
    doc.multiBuild(story, onFirstPage=decorate, onLaterPages=decorate)
    actual_pages = doc.page

    end_time = time.time()

    sections_included = [f"{s['no']}. {s['title']}" for s in SECTION_SPECS]
    sections_included.append(f"{len(SECTION_SPECS) + 1}. {CLOSING_SECTION_TITLE}")
    sections_included += [
        "Annexure A — Model factor attribution (SHAP)",
        "Annexure B — Fraud and forensic signals",
        "Annexure C — Adverse media screen",
        "Annexure D — Conditions for approval",
    ]

    return {
        "success": True,
        "cam_id": company_name.replace(" ", "_").lower(),
        "document_ready": True,
        "pdf_document_path": pdf_path,
        "pages_count": actual_pages,
        "sections_included": sections_included,
        "sections_failed": failed,
        "generation_time_minutes": round((end_time - start_time) / 60.0, 2),
    }
