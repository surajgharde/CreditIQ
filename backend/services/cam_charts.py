"""
Charts for the Credit Appraisal Memorandum.

Rendered with matplotlib to PNG and embedded as ReportLab Images. Every builder
returns an empty list when its inputs are missing, so a thin borrower file
simply yields fewer figures instead of a broken or — worse — a fabricated chart.

Colour roles follow one validated palette (see PALETTE below): categorical hues
are assigned in fixed order and never cycled, magnitude uses a single hue,
polarity uses the blue/red diverging pair with a neutral midpoint, and the
status colours are reserved for risk state and always ship beside a text label.
"""
import os
import time
import uuid
import logging
from typing import Optional

import matplotlib

# Headless: the API process has no display.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Image  # noqa: E402

logger = logging.getLogger(__name__)

CHARTS_DIR = os.path.join(os.getcwd(), "graphs", "cam")
os.makedirs(CHARTS_DIR, exist_ok=True)

# Figures are intermediate: ReportLab reads them during the build and the PDF
# embeds the bytes, so nothing needs them afterwards. Unique filenames stop
# concurrent builds colliding, which means they would otherwise accumulate.
CHART_RETENTION_SECONDS = 3600


def _prune_old_charts() -> None:
    """Drops figures left by earlier builds. Never raises — this is housekeeping."""
    cutoff = time.time() - CHART_RETENTION_SECONDS
    try:
        for entry in os.scandir(CHARTS_DIR):
            if entry.name.endswith(".png") and entry.stat().st_mtime < cutoff:
                os.remove(entry.path)
    except OSError:
        pass

# ---------------------------------------------------------------------------
# Palette — one validated instance, referenced by role, never by raw hex below.
# ---------------------------------------------------------------------------
PALETTE = {
    "surface": "#fcfcfb",
    "text_primary": "#0b0b0b",
    "text_secondary": "#52514e",
    "text_muted": "#7a7975",
    "grid": "#e4e3df",
    # Categorical, fixed order.
    "series_1": "#2a78d6",   # blue
    "series_2": "#eb6834",   # orange
    "series_3": "#1baf7a",   # aqua
    # Diverging poles + neutral midpoint.
    "diverge_pos": "#e34948",  # red — pushes PD up
    "diverge_neg": "#2a78d6",  # blue — pulls PD down
    "diverge_mid": "#f0efec",
    # Status — reserved, never reused as a series colour.
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

DPI = 200
BAR_HEIGHT = 0.55          # thin marks
SURFACE_GAP = 1.6          # points of surface showing between adjacent fills


def _style_axes(ax, xlabel: str = "") -> None:
    """Recessive grid and axes; no chartjunk."""
    ax.set_facecolor(PALETTE["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(PALETTE["grid"])
    ax.spines["bottom"].set_linewidth(0.8)
    ax.tick_params(axis="both", colors=PALETTE["text_secondary"],
                   labelsize=7.5, length=0)
    ax.xaxis.grid(True, color=PALETTE["grid"], linewidth=0.7)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, color=PALETTE["text_secondary"], fontsize=7.5)


def _save(fig, name: str, width_mm: float) -> list:
    """
    Writes the figure and returns it as a ReportLab flowable.

    The filename carries a unique suffix: CAM generation runs in a worker
    thread and two memos built at once would otherwise write the same
    graphs/cam/<name>.png and swap each other's figures mid-build.
    """
    _prune_old_charts()
    path = os.path.join(CHARTS_DIR, f"{name}_{uuid.uuid4().hex[:12]}.png")
    try:
        fig.savefig(path, dpi=DPI, facecolor=PALETTE["surface"],
                    bbox_inches="tight", pad_inches=0.12)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not render CAM chart %s: %s", name, exc)
        return []
    finally:
        plt.close(fig)

    try:
        img = Image(path)
        scale = (width_mm * mm) / img.imageWidth
        img.drawWidth = width_mm * mm
        img.drawHeight = img.imageHeight * scale
        img.hAlign = "LEFT"
        return [img]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not embed CAM chart %s: %s", name, exc)
        return []


def _money_fmt(value) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return ""
    if abs(num) >= 1_00_00_000:
        return f"{num / 1_00_00_000:,.2f} Cr"
    if abs(num) >= 1_00_000:
        return f"{num / 1_00_000:,.2f} L"
    return f"{num:,.0f}"


# ---------------------------------------------------------------------------
# 1. Risk position — a single headline, so a band strip with one marker rather
#    than a chart that implies a trend the data does not have.
# ---------------------------------------------------------------------------

def risk_position_chart(pd_value, decision: str, width_mm: float) -> list:
    try:
        pd_num = float(pd_value)
    except (TypeError, ValueError):
        return []

    bands = [
        (0, 15, PALETTE["good"], "Low"),
        (15, 30, PALETTE["warning"], "Moderate"),
        (30, 60, PALETTE["serious"], "Elevated"),
        (60, 100, PALETTE["critical"], "Severe"),
    ]

    fig, ax = plt.subplots(figsize=(7.2, 1.5))
    fig.patch.set_facecolor(PALETTE["surface"])
    ax.set_facecolor(PALETTE["surface"])

    for start, end, colour, label in bands:
        # 2pt of surface between adjacent fills.
        ax.barh(0, end - start - 0.4, left=start + 0.2, height=0.42,
                color=colour, edgecolor=PALETTE["surface"], linewidth=SURFACE_GAP)
        ax.text((start + end) / 2, -0.52, label, ha="center", va="top",
                fontsize=7, color=PALETTE["text_secondary"])

    marker = min(max(pd_num, 0.0), 100.0)
    # A 2px surface ring so the marker reads against whichever band it lands on.
    ax.plot([marker], [0], marker="v", markersize=11,
            color=PALETTE["text_primary"],
            markeredgecolor=PALETTE["surface"], markeredgewidth=2, zorder=5)
    ax.text(marker, 0.42, f"PD {pd_num:.1f}%  ·  {str(decision or 'PENDING').upper()}",
            ha="center", va="bottom", fontsize=9, fontweight="bold",
            color=PALETTE["text_primary"])

    ax.set_xlim(0, 100)
    ax.set_ylim(-0.95, 0.95)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="x", colors=PALETTE["text_secondary"], labelsize=7.5, length=0)

    return _save(fig, "risk_position", width_mm)


# ---------------------------------------------------------------------------
# 2. Ratios against the sector benchmark — two series, so a legend is required.
# ---------------------------------------------------------------------------

def ratio_benchmark_chart(financials: dict, benchmarks: dict, width_mm: float) -> list:
    """
    Each ratio indexed to its own sector benchmark (1.0x = at benchmark).

    Plotting the raw values side by side put a percentage (EBITDA margin ~16)
    and three multiples (~0.4 to ~5) on one linear axis, which squashed the
    multiples to invisible stubs. Indexing to a common base is the fix; the
    absolute figures sit in the accompanying table.

    Colour carries whether the variance is favourable, which is not the same as
    "above benchmark" — a high debt/equity is adverse while a high current ratio
    is favourable — so direction is set per ratio, not by sign.
    """
    # (label, key, benchmark, higher_is_better)
    specs = [
        ("Current ratio", "current_ratio", benchmarks.get("current_ratio"), True),
        ("Debt / equity", "debt_to_equity", benchmarks.get("debt_to_equity"), False),
        ("Interest cover", "interest_coverage", benchmarks.get("interest_coverage"), True),
        ("EBITDA margin %", "ebitda_margin_percent",
         benchmarks.get("ebitda_margin_percent"), True),
    ]
    rows = []
    for label, key, bench, higher_better in specs:
        if financials.get(key) is None or not bench:
            continue
        actual = float(financials[key])
        bench = float(bench)
        if bench == 0:
            continue
        indexed = actual / bench
        favourable = (indexed >= 1.0) if higher_better else (indexed <= 1.0)
        rows.append((label, actual, bench, indexed, favourable))
    if not rows:
        return []

    rows.reverse()
    fig, ax = plt.subplots(figsize=(7.2, 0.58 * len(rows) + 1.3))
    fig.patch.set_facecolor(PALETTE["surface"])

    values = [r[3] for r in rows]
    colours = [PALETTE["diverge_neg"] if r[4] else PALETTE["diverge_pos"] for r in rows]
    ax.barh(range(len(rows)), values, height=BAR_HEIGHT, color=colours,
            edgecolor=PALETTE["surface"], linewidth=SURFACE_GAP)

    span = max(values + [1.0])
    for i, (label, actual, bench, indexed, favourable) in enumerate(rows):
        ax.text(indexed + span * 0.02, i,
                f"{indexed:.2f}x    ({actual:,.2f} vs {bench:,.2f})",
                va="center", fontsize=7.5, color=PALETTE["text_primary"])

    # The common base. Neutral, so it reads as "nothing", not as a series.
    # Deliberately unlabelled: a floating "benchmark" caption collided with the
    # favourable/adverse captions above and the axis label below, and the axis
    # label already states what the line is.
    ax.axvline(1.0, color=PALETTE["text_muted"], linewidth=1.0, linestyle="--")

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8,
                       color=PALETTE["text_primary"])
    ax.set_xlim(0, span * 1.75)
    _style_axes(ax, "Borrower value indexed to sector benchmark (1.00x = at benchmark)")

    # Two colours carry meaning, so both are named.
    ax.text(0.0, 1.03, "Favourable variance", transform=ax.transAxes, ha="left",
            va="bottom", fontsize=7.5, color=PALETTE["diverge_neg"], fontweight="bold")
    ax.text(1.0, 1.03, "Adverse variance", transform=ax.transAxes, ha="right",
            va="bottom", fontsize=7.5, color=PALETTE["diverge_pos"], fontweight="bold")

    return _save(fig, "ratio_benchmark", width_mm)


# ---------------------------------------------------------------------------
# 3. SHAP attribution — polarity, so the diverging pair about a zero midpoint.
# ---------------------------------------------------------------------------

def shap_attribution_chart(shap_factors: list, width_mm: float) -> list:
    parsed = []
    for factor in shap_factors or []:
        raw = str(factor.get("impact", "")).strip().replace("+", "")
        try:
            parsed.append((str(factor.get("name", "Unnamed")), float(raw)))
        except ValueError:
            continue
    if not parsed:
        return []

    parsed = sorted(parsed, key=lambda p: abs(p[1]), reverse=True)[:10]
    parsed.reverse()  # largest at the top of a horizontal chart

    labels = [p[0] for p in parsed]
    values = [p[1] for p in parsed]
    colours = [PALETTE["diverge_pos"] if v >= 0 else PALETTE["diverge_neg"] for v in values]

    fig, ax = plt.subplots(figsize=(7.2, 0.42 * len(parsed) + 1.2))
    fig.patch.set_facecolor(PALETTE["surface"])

    ax.barh(range(len(parsed)), values, height=BAR_HEIGHT, color=colours,
            edgecolor=PALETTE["surface"], linewidth=SURFACE_GAP)

    reach = max(abs(v) for v in values) or 1.0
    for i, v in enumerate(values):
        ax.text(v + (reach * 0.02 if v >= 0 else -reach * 0.02), i,
                f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right",
                fontsize=7.5, color=PALETTE["text_primary"])

    # Neutral midpoint, not a hue.
    ax.axvline(0, color=PALETTE["text_muted"], linewidth=0.9)
    ax.set_yticks(range(len(parsed)))
    ax.set_yticklabels(labels, fontsize=8, color=PALETTE["text_primary"])
    ax.set_xlim(-reach * 1.3, reach * 1.3)
    _style_axes(ax, "Contribution to probability of default")

    # Two colours carry meaning, so they are named rather than left to hue.
    # Placed above the plot in axes coordinates: at the foot they collided with
    # the outermost x tick labels.
    ax.text(1.0, 1.02, "Increases PD", transform=ax.transAxes, ha="right",
            va="bottom", fontsize=7.5, color=PALETTE["diverge_pos"],
            fontweight="bold")
    ax.text(0.0, 1.02, "Reduces PD", transform=ax.transAxes, ha="left",
            va="bottom", fontsize=7.5, color=PALETTE["diverge_neg"],
            fontweight="bold")

    return _save(fig, "shap_attribution", width_mm)


# ---------------------------------------------------------------------------
# 4. Financial position — magnitude, one hue, single series so no legend.
# ---------------------------------------------------------------------------

def financial_position_chart(financials: dict, width_mm: float) -> list:
    specs = [
        ("Revenue", "revenue_fy24"),
        ("Gross profit", "gross_profit"),
        ("EBITDA", "ebitda"),
        ("Net profit", "net_profit"),
        ("Total assets", "total_assets"),
        ("Total equity", "total_equity"),
        ("Total borrowings", "total_debt"),
    ]
    rows = [(label, float(financials[key])) for label, key in specs
            if financials.get(key) is not None]
    if len(rows) < 2:
        return []

    rows.reverse()
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(7.2, 0.46 * len(rows) + 1.0))
    fig.patch.set_facecolor(PALETTE["surface"])

    ax.barh(range(len(rows)), values, height=BAR_HEIGHT,
            color=PALETTE["series_1"],
            edgecolor=PALETTE["surface"], linewidth=SURFACE_GAP)

    span = max(abs(v) for v in values) or 1.0
    for i, v in enumerate(values):
        ax.text(v + span * 0.015, i, _money_fmt(v), va="center", fontsize=7.5,
                color=PALETTE["text_primary"])

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(labels, fontsize=8, color=PALETTE["text_primary"])
    ax.set_xlim(min(0, min(values) * 1.2), span * 1.22)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: _money_fmt(v)))
    _style_axes(ax)

    return _save(fig, "financial_position", width_mm)


# ---------------------------------------------------------------------------
# 5. Fraud signals — status colours, always beside the signal name.
# ---------------------------------------------------------------------------

RISK_COLOUR = {
    "CRITICAL": PALETTE["critical"],
    "HIGH": PALETTE["critical"],
    "MEDIUM": PALETTE["serious"],
    "LOW": PALETTE["warning"],
}


def fraud_signal_chart(signals: list, width_mm: float) -> list:
    rows = []
    for sig in signals or []:
        amount = sig.get("evidence_amount")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        name = str(sig.get("signal_type") or sig.get("description") or "Signal")
        rows.append((name.replace("_", " ").title()[:34],
                     amount,
                     str(sig.get("risk_level") or "MEDIUM").upper()))
    if not rows:
        return []

    rows = sorted(rows, key=lambda r: r[1])[-8:]
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    colours = [RISK_COLOUR.get(r[2], PALETTE["serious"]) for r in rows]

    fig, ax = plt.subplots(figsize=(7.2, 0.48 * len(rows) + 1.0))
    fig.patch.set_facecolor(PALETTE["surface"])

    ax.barh(range(len(rows)), values, height=BAR_HEIGHT, color=colours,
            edgecolor=PALETTE["surface"], linewidth=SURFACE_GAP)

    span = max(values) or 1.0
    for i, (v, row) in enumerate(zip(values, rows)):
        # Status colour never carries the meaning alone — the level is written out.
        ax.text(v + span * 0.015, i, f"{_money_fmt(v)}  ({row[2]})", va="center",
                fontsize=7.5, color=PALETTE["text_primary"])

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(labels, fontsize=8, color=PALETTE["text_primary"])
    ax.set_xlim(0, span * 1.32)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: _money_fmt(v)))
    _style_axes(ax, "Evidence amount")

    return _save(fig, "fraud_signals", width_mm)


# ---------------------------------------------------------------------------
# 6. Facility requested vs recommended — two bars, labelled directly.
# ---------------------------------------------------------------------------

def facility_chart(requested, recommended, width_mm: float) -> list:
    try:
        req = float(requested)
        rec = float(recommended)
    except (TypeError, ValueError):
        return []
    if req <= 0:
        return []

    fig, ax = plt.subplots(figsize=(7.2, 1.9))
    fig.patch.set_facecolor(PALETTE["surface"])

    ax.barh([1], [req], height=BAR_HEIGHT, color=PALETTE["series_1"],
            edgecolor=PALETTE["surface"], linewidth=SURFACE_GAP)
    ax.barh([0], [rec], height=BAR_HEIGHT, color=PALETTE["series_3"],
            edgecolor=PALETTE["surface"], linewidth=SURFACE_GAP)

    for y, value in ((1, req), (0, rec)):
        ax.text(value + req * 0.015, y, _money_fmt(value), va="center",
                fontsize=8, color=PALETTE["text_primary"])

    haircut = (1 - rec / req) * 100 if req else 0
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Recommended", "Requested"], fontsize=8,
                       color=PALETTE["text_primary"])
    ax.set_xlim(0, req * 1.25)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: _money_fmt(v)))
    _style_axes(ax, f"Haircut applied: {haircut:.1f}%")

    return _save(fig, "facility", width_mm)
