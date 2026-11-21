"""
The feature contract for the credit PD model.

One module defines the features, their order and their clipping bounds, and both
sides import it: `train_model.py` when it builds the training matrix from the
public bankruptcy dataset, and `scoring_service.py` when it builds a single row
from a borrower's extracted statements. Training and inference therefore cannot
drift apart.

Every feature is a firm-level ratio computable from a balance sheet, a profit
and loss statement and (for the last one) a cash flow statement. A ratio that
the document reader could not produce is passed through as NaN — XGBoost learns
a default direction for missing values, which is honest about the gap. It is not
replaced with an invented "typical" number, because a decision computed from
invented inputs looks identical to one computed from real inputs.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Ordered feature names. The model is trained on exactly this order.
FEATURES: Tuple[str, ...] = (
    "current_ratio",
    "quick_ratio",
    "debt_to_assets",
    "debt_to_equity",
    "interest_coverage",
    "gross_margin_percent",
    "ebitda_margin_percent",
    "net_margin_percent",
    "return_on_assets_percent",
    "asset_turnover",
    "working_capital_to_assets",
    "cash_flow_to_debt",
)

# Human-readable definition of each feature, used in the README, the API
# response and the SHAP labels.
FEATURE_DEFINITIONS: Dict[str, str] = {
    "current_ratio": "Current assets / current liabilities",
    "quick_ratio": "(Current assets - inventory) / current liabilities",
    "debt_to_assets": "Total liabilities / total assets",
    "debt_to_equity": "Total liabilities / shareholders' equity",
    "interest_coverage": "EBIT / interest expense",
    "gross_margin_percent": "Gross profit / revenue, per cent",
    "ebitda_margin_percent": "EBITDA / revenue, per cent",
    "net_margin_percent": "Net profit after tax / revenue, per cent",
    "return_on_assets_percent": "Net profit after tax / total assets, per cent",
    "asset_turnover": "Revenue / total assets",
    "working_capital_to_assets": "(Current assets - current liabilities) / total assets",
    "cash_flow_to_debt": "Cash flow from operations / total liabilities",
}

# Ratios computed from reported statements have heavy tails: a company with
# near-zero equity produces a debt-to-equity in the thousands, and such a row
# would otherwise dominate the splits. Bounds are applied identically to the
# training matrix and to every inference row.
CLIPS: Dict[str, Tuple[float, float]] = {
    "current_ratio": (0.0, 20.0),
    "quick_ratio": (0.0, 20.0),
    "debt_to_assets": (0.0, 5.0),
    "debt_to_equity": (-50.0, 50.0),
    "interest_coverage": (-50.0, 100.0),
    "gross_margin_percent": (-200.0, 100.0),
    "ebitda_margin_percent": (-200.0, 100.0),
    "net_margin_percent": (-200.0, 100.0),
    "return_on_assets_percent": (-100.0, 100.0),
    "asset_turnover": (0.0, 20.0),
    "working_capital_to_assets": (-5.0, 1.0),
    "cash_flow_to_debt": (-5.0, 5.0),
}


def clip_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the shared bounds, leaving NaN as NaN."""
    out = frame.copy()
    for name, (low, high) in CLIPS.items():
        if name in out.columns:
            out[name] = pd.to_numeric(out[name], errors="coerce").clip(low, high)
    return out[list(FEATURES)]


def _ratio(numerator: Any, denominator: Any) -> float:
    """A ratio, or NaN when either side is missing or the denominator is zero."""
    try:
        num = float(numerator)
        den = float(denominator)
    except (TypeError, ValueError):
        return math.nan
    if not math.isfinite(num) or not math.isfinite(den) or den == 0.0:
        return math.nan
    return num / den


def features_from_financials(extracted: Dict[str, Any]) -> Tuple[Dict[str, float], List[str]]:
    """
    Build one model row from the statement lines the document reader extracted.

    Returns the feature values and the names of the features that could not be
    computed because a required statement line was not read. The caller is
    expected to report the second list rather than hide it.
    """
    get = extracted.get

    revenue = get("revenue_fy24")
    total_assets = get("total_assets")
    total_liabilities = get("total_liabilities")
    total_equity = get("total_equity")
    current_assets = get("current_assets")
    current_liabilities = get("current_liabilities")
    inventory = get("inventory")
    operating_cash_flow = get("operating_cash_flow")

    # Liabilities can be derived when the statement reports assets and equity
    # but not the liabilities total, since a balance sheet balances.
    if total_liabilities is None and total_assets is not None and total_equity is not None:
        try:
            total_liabilities = float(total_assets) - float(total_equity)
        except (TypeError, ValueError):
            total_liabilities = None

    working_capital = math.nan
    if current_assets is not None and current_liabilities is not None:
        try:
            working_capital = float(current_assets) - float(current_liabilities)
        except (TypeError, ValueError):
            working_capital = math.nan

    quick_assets = math.nan
    if current_assets is not None:
        try:
            quick_assets = float(current_assets) - float(inventory or 0.0)
        except (TypeError, ValueError):
            quick_assets = math.nan

    values: Dict[str, float] = {
        "current_ratio": _ratio(current_assets, current_liabilities),
        "quick_ratio": _ratio(quick_assets, current_liabilities),
        "debt_to_assets": _ratio(total_liabilities, total_assets),
        "debt_to_equity": _ratio(total_liabilities, total_equity),
        "interest_coverage": _ratio(get("ebit"), get("interest_expense")),
        "gross_margin_percent": _ratio(get("gross_profit"), revenue) * 100.0,
        "ebitda_margin_percent": _ratio(get("ebitda"), revenue) * 100.0,
        "net_margin_percent": _ratio(get("net_profit"), revenue) * 100.0,
        "return_on_assets_percent": _ratio(get("net_profit"), total_assets) * 100.0,
        "asset_turnover": _ratio(revenue, total_assets),
        "working_capital_to_assets": _ratio(working_capital, total_assets),
        "cash_flow_to_debt": _ratio(operating_cash_flow, total_liabilities),
    }

    missing = [name for name in FEATURES if not math.isfinite(values[name])]
    return values, missing


def frame_from_financials(extracted: Dict[str, Any]) -> Tuple[pd.DataFrame, List[str]]:
    """features_from_financials, shaped and clipped ready for predict_proba."""
    values, missing = features_from_financials(extracted)
    frame = pd.DataFrame([{name: values[name] for name in FEATURES}], dtype=float)
    return clip_frame(frame), missing


def ks_statistic(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """
    Kolmogorov-Smirnov separation: the largest gap between the cumulative
    distribution of scores for defaulters and for non-defaulters.
    """
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score, dtype=float)
    positives = y_score[y_true == 1]
    negatives = y_score[y_true == 0]
    if positives.size == 0 or negatives.size == 0:
        return float("nan")
    thresholds = np.sort(np.unique(y_score))
    pos_cdf = np.searchsorted(np.sort(positives), thresholds, side="right") / positives.size
    neg_cdf = np.searchsorted(np.sort(negatives), thresholds, side="right") / negatives.size
    return float(np.max(np.abs(pos_cdf - neg_cdf)))
