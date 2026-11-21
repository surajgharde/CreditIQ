"""
Credit scoring: probability of default, SHAP attribution, pricing and sizing.

What the model is
-----------------
One XGBoost classifier, trained by `train_model.py` on the UCI "Polish
companies bankruptcy" dataset (10,503 firms, 64 reported financial ratios).
Its twelve features are firm-level ratios — the ones `services/credit_features.py`
defines — and nothing else. Held-out ROC-AUC, KS and calibration are recorded in
`models/xgboost/metrics.json` by the training run that produced the model file.

What the model is not
---------------------
It does not score fraud or news. Those have no labels in any dataset here, so
they cannot be features; inventing a column for them was how the previous
version worked, and it meant the PD moved for reasons the model had never been
trained on. Fraud and adverse news now enter where they can be stated plainly:
the underwriting decision and the risk premium, both rule-based and both printed
in the response.

Missing inputs
--------------
A ratio whose statement line was not extracted is passed to XGBoost as NaN, and
XGBoost routes missing values down the branch it learned for them. It is not
replaced by a plausible-looking default, because a decision computed from
invented inputs is indistinguishable from one computed from real inputs. Every
ratio that was missing is listed in the response as `features_not_extracted`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import joblib
import matplotlib
import numpy as np
import pandas as pd
import shap

matplotlib.use("Agg")  # headless: no display needed to render the SHAP plot
import matplotlib.pyplot as plt  # noqa: E402

from services.credit_features import (  # noqa: E402
    FEATURE_DEFINITIONS,
    FEATURES,
    frame_from_financials,
)
from services.external_apis import cache_get, cache_set  # noqa: E402

logger = logging.getLogger(__name__)

# Anchored to the backend directory rather than the working directory, so the
# model is found regardless of where the server was started from.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BACKEND_DIR, "models", "xgboost")
GRAPHS_DIR = os.path.join(BACKEND_DIR, "graphs")
MODEL_PATH = os.path.join(MODELS_DIR, "creditiq_pd_xgboost.pkl")
METRICS_PATH = os.path.join(MODELS_DIR, "metrics.json")
os.makedirs(GRAPHS_DIR, exist_ok=True)

# Pricing matrix. Every number here is a stated policy choice, not a model
# output, and the response breaks the final rate back down into these parts.
REPO_RATE_PERCENT = 6.5
PD_SPREAD_BANDS = ((10.0, 1.5), (20.0, 3.0), (30.0, 4.5), (40.0, 6.0))
PD_SPREAD_ABOVE_TOP_BAND = 8.0
# UNKNOWN means the fraud checks could not run. It is priced like MEDIUM rather
# than like LOW: an unperformed check is not a passed check.
FRAUD_PREMIUM = {"HIGH": 2.0, "MEDIUM": 1.0, "UNKNOWN": 1.0, "LOW": 0.0}
NEWS_PREMIUM_THRESHOLD = 60.0
NEWS_PREMIUM = 0.5

# Underwriting policy thresholds.
REJECT_PD_PERCENT = 50.0
CONDITIONAL_PD_PERCENT = 25.0

# Sizing policy: the minimum debt service cover the book will underwrite to, and
# the amortisation term the sizing assumes.
MIN_DSCR = 1.2
SIZING_TERM_YEARS = 5

_BUNDLE: Optional[Dict[str, Any]] = None


class ModelNotTrained(RuntimeError):
    """Raised when no trained model file is present."""


def load_model_bundle() -> Dict[str, Any]:
    """
    Load the booster, its calibrator and its feature order, once per process.

    There is deliberately no train-on-first-use path. Training downloads a
    dataset and takes minutes; doing that inside a request made the first
    analysis of the day behave unlike every other one, and an untrained
    deployment would silently score with whatever model file happened to exist.
    """
    global _BUNDLE
    if _BUNDLE is not None:
        return _BUNDLE

    if not os.path.exists(MODEL_PATH):
        raise ModelNotTrained(
            f"No trained model at {MODEL_PATH}. Run `python train_model.py` from "
            "the backend directory; it downloads the public bankruptcy dataset, "
            "trains the model and writes its held-out metrics to metrics.json."
        )

    bundle = joblib.load(MODEL_PATH)
    if not isinstance(bundle, dict) or "model" not in bundle:
        raise ModelNotTrained(
            f"{MODEL_PATH} is not a CreditIQ model bundle. Retrain with "
            "`python train_model.py` to regenerate it."
        )

    features = tuple(bundle.get("features", ()))
    if features != FEATURES:
        raise ModelNotTrained(
            "The model file was trained on a different feature set than "
            f"services/credit_features.py defines.\n  model: {features}\n  code:  {FEATURES}\n"
            "Retrain with `python train_model.py`."
        )

    _BUNDLE = bundle
    metrics = bundle.get("test_metrics", {})
    logger.info(
        "Loaded PD model trained %s (held-out ROC-AUC %s, KS %s)",
        bundle.get("trained_at", "unknown"),
        metrics.get("roc_auc", "?"),
        metrics.get("ks", "?"),
    )
    return bundle


def model_card() -> Dict[str, Any]:
    """The model's provenance and held-out performance, for display and audit."""
    try:
        bundle = load_model_bundle()
    except ModelNotTrained as exc:
        return {"available": False, "detail": str(exc)}

    card: Dict[str, Any] = {
        "available": True,
        "trained_at": bundle.get("trained_at"),
        "features": list(FEATURES),
        "held_out": bundle.get("test_metrics", {}),
    }
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, "r", encoding="utf-8") as handle:
                full = json.load(handle)
            card["dataset"] = full.get("dataset")
            card["calibration"] = full.get("calibration")
            card["hyperparameters"] = full.get("hyperparameters")
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read %s: %s", METRICS_PATH, exc)
    return card


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _calibrated_pd(calibrator, raw_probability: float) -> float:
    """Map a raw booster probability onto the calibrated default frequency."""
    if calibrator is None:
        return float(raw_probability)
    return float(calibrator.predict([raw_probability])[0])


def _credit_spread(pd_percent: float) -> float:
    for ceiling, spread in PD_SPREAD_BANDS:
        if pd_percent <= ceiling:
            return spread
    return PD_SPREAD_ABOVE_TOP_BAND


def _annuity_factor(annual_rate_percent: float, years: int) -> float:
    """
    Present value of one unit paid annually for `years`, at `annual_rate_percent`.

    Sizing a loan off cash flow means asking what principal an affordable annual
    payment can service at the rate being offered — not multiplying the payment
    by the term, which ignores interest entirely.
    """
    rate = annual_rate_percent / 100.0
    if rate <= 0:
        return float(years)
    return (1.0 - (1.0 + rate) ** -years) / rate


def _shap_attribution(model, calibrator, frame: pd.DataFrame, final_pd: float
                      ) -> Tuple[List[Dict[str, Any]], float, Any]:
    """
    Per-feature attribution, reported in PD percentage points.

    TreeExplainer works in log-odds. A log-odds number means nothing on a credit
    memo, and it cannot be multiplied by a constant to become a percentage
    either — which is what the previous version did. Each feature's effect is
    instead measured where it is read: the PD with that feature's contribution
    removed from the margin, against the PD with it. The parts are therefore not
    exactly additive (the logistic link is not linear), and the response says so.
    """
    explainer = shap.TreeExplainer(model)
    explanation = explainer(frame)

    shap_values = np.asarray(explanation.values[0], dtype=float)
    base_margin = float(np.ravel(explanation.base_values)[0])
    total_margin = base_margin + float(np.sum(shap_values))

    base_pd = 100.0 * _calibrated_pd(calibrator, _sigmoid(base_margin))

    factors: List[Dict[str, Any]] = []
    for index, name in enumerate(FEATURES):
        contribution = shap_values[index]
        pd_without = 100.0 * _calibrated_pd(
            calibrator, _sigmoid(total_margin - contribution)
        )
        impact = final_pd - pd_without
        value = frame.iloc[0][name]
        factors.append({
            "name": name.replace("_", " ").title(),
            "feature": name,
            "definition": FEATURE_DEFINITIONS[name],
            "value": None if pd.isna(value) else round(float(value), 3),
            "extracted": bool(not pd.isna(value)),
            "impact": f"{'+' if impact > 0 else ''}{impact:.1f}",
            "impact_pd_points": round(impact, 2),
            "shap_log_odds": round(float(contribution), 4),
        })

    factors.sort(key=lambda factor: abs(factor["impact_pd_points"]), reverse=True)
    return factors, round(base_pd, 2), explanation


def _render_waterfall(explanation) -> str:
    """Write the SHAP waterfall and return the URL the frontend fetches."""
    plt.figure(figsize=(12, 8))
    shap.plots.waterfall(explanation[0], max_display=12, show=False)
    plt.title("SHAP contribution to default log-odds", fontsize=13)
    plt.tight_layout()
    filename = f"shap_waterfall_{uuid.uuid4().hex[:8]}.png"
    plt.savefig(os.path.join(GRAPHS_DIR, filename), format="png", dpi=200, bbox_inches="tight")
    plt.close()
    return f"/graphs/{filename}"


def _size_loan(operating_cash_flow: Optional[float], loan_amount_requested: float,
               interest_rate: float) -> Tuple[Optional[float], str]:
    """
    Size the facility off cash flow from operations, or decline to size it.

    The previous version defaulted operating cash flow to 10% of the requested
    amount whenever it was not extracted — which it never was, because nothing
    extracted it. Every recommendation was therefore the same fraction of every
    request. When the line is genuinely absent the amount is now reported as not
    available, which is a thing a credit officer can act on.
    """
    if operating_cash_flow is None:
        return None, (
            "Not sized: cash flow from operations was not extracted from the "
            "submitted documents. Supply a cash flow statement to size the facility."
        )

    try:
        cash_flow = float(operating_cash_flow)
    except (TypeError, ValueError):
        return None, (
            "Not sized: the extracted cash flow from operations was not a number."
        )

    if cash_flow <= 0:
        return 0.0, (
            f"Cash flow from operations is {cash_flow:,.0f}, so there is no cash "
            f"available to service debt at the {MIN_DSCR}x cover floor."
        )

    affordable_annual_payment = cash_flow / MIN_DSCR
    max_supportable = affordable_annual_payment * _annuity_factor(
        interest_rate, SIZING_TERM_YEARS
    )
    sized = min(loan_amount_requested, max_supportable)
    basis = (
        f"Cash flow from operations {cash_flow:,.0f} supports an annual debt "
        f"service of {affordable_annual_payment:,.0f} at the {MIN_DSCR}x cover "
        f"floor, which services {max_supportable:,.0f} over {SIZING_TERM_YEARS} "
        f"years at {interest_rate:.2f}%."
    )
    if sized < loan_amount_requested:
        basis += " The request exceeds that, so the recommendation is capped at it."
    else:
        basis += " The request is within that, so it is recommended in full."
    return float(sized), basis


def _decide(pd_percent: float, fraud_level: str) -> Tuple[str, List[str]]:
    """
    The underwriting decision.

    REJECT was unreachable before: both branches that should have produced it
    returned CONDITIONAL, with a comment saying this was "to ensure valid
    processed workflows pass". A model that cannot decline is not an
    underwriting model.
    """
    reasons: List[str] = []
    if pd_percent > REJECT_PD_PERCENT:
        reasons.append(
            f"Probability of default {pd_percent:.1f}% is above the "
            f"{REJECT_PD_PERCENT:.0f}% decline threshold."
        )
    if fraud_level == "HIGH":
        reasons.append("Fraud screening returned HIGH risk.")
    if reasons:
        return "REJECT", reasons

    if pd_percent > CONDITIONAL_PD_PERCENT:
        reasons.append(
            f"Probability of default {pd_percent:.1f}% is above the "
            f"{CONDITIONAL_PD_PERCENT:.0f}% straight-through threshold."
        )
    if fraud_level == "MEDIUM":
        reasons.append("Fraud screening returned MEDIUM risk.")
    if fraud_level == "UNKNOWN":
        reasons.append(
            "Fraud screening could not run: no GST, ledger or director data was "
            "available. The checks are outstanding, not passed."
        )
    if reasons:
        return "CONDITIONAL", reasons

    return "APPROVE", [
        f"Probability of default {pd_percent:.1f}% is within the "
        f"{CONDITIONAL_PD_PERCENT:.0f}% straight-through threshold and fraud "
        "screening returned LOW risk."
    ]


def calculate_credit_score(extracted_data: Dict[str, Any], fraud_flags: str,
                           news_score: float, loan_amount_requested: float) -> Dict[str, Any]:
    """
    Score one application.

    `extracted_data` is the document reader's output. `fraud_flags` is the fraud
    engine's overall level and `news_score` the adverse-media score: neither
    enters the model, both enter the decision and the price.
    """
    bundle = load_model_bundle()
    model = bundle["model"]
    calibrator = bundle.get("calibrator")

    frame, missing = frame_from_financials(extracted_data)
    if len(missing) == len(FEATURES):
        return {
            "error": (
                "No financial ratio could be computed from the extracted documents, "
                "so no probability of default can be produced. Required statement "
                "lines: revenue, total assets, total liabilities or equity, current "
                "assets and current liabilities."
            )
        }

    flags = (fraud_flags or "").upper()
    if "HIGH" in flags:
        fraud_level = "HIGH"
    elif "MEDIUM" in flags:
        fraud_level = "MEDIUM"
    elif "UNKNOWN" in flags or not flags:
        # No level at all also means the screen did not produce one.
        fraud_level = "UNKNOWN"
    else:
        fraud_level = "LOW"
    news_score = float(news_score or 0.0)

    cache_key = "pd_" + hashlib.sha256(
        json.dumps(
            {
                "features": {name: (None if pd.isna(v) else float(v))
                             for name, v in frame.iloc[0].items()},
                "fraud": fraud_level,
                "news": round(news_score, 2),
                "loan": float(loan_amount_requested or 0.0),
                "model": bundle.get("trained_at"),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    cached = cache_get(cache_key)
    if cached:
        return cached

    raw_probability = float(model.predict_proba(frame)[0][1])
    probability_of_default = 100.0 * _calibrated_pd(calibrator, raw_probability)

    shap_factors, base_risk, explanation = _shap_attribution(
        model, calibrator, frame, probability_of_default
    )
    try:
        chart_url = _render_waterfall(explanation)
    except Exception as exc:  # a failed plot must not fail the appraisal
        logger.warning("SHAP waterfall rendering failed: %s", exc)
        chart_url = ""

    # Pricing: repo rate plus stated premiums.
    credit_spread = _credit_spread(probability_of_default)
    fraud_premium = FRAUD_PREMIUM[fraud_level]
    news_premium = NEWS_PREMIUM if news_score >= NEWS_PREMIUM_THRESHOLD else 0.0
    interest_rate = round(
        REPO_RATE_PERCENT + credit_spread + fraud_premium + news_premium, 2
    )

    decision, decision_reasons = _decide(probability_of_default, fraud_level)
    recommended_loan, sizing_basis = _size_loan(
        extracted_data.get("operating_cash_flow"), float(loan_amount_requested or 0.0), interest_rate
    )
    if decision == "REJECT":
        recommended_loan = 0.0
        sizing_basis = "Declined, so no amount is recommended. " + sizing_basis

    data_completeness = round(100.0 * (len(FEATURES) - len(missing)) / len(FEATURES), 1)
    reasoning = " ".join(decision_reasons) + (
        f" The probability of default is the calibrated output of the gradient-boosted "
        f"model on {len(FEATURES) - len(missing)} of {len(FEATURES)} financial ratios "
        f"({data_completeness}% of the feature set was extractable). "
        f"Pricing is {REPO_RATE_PERCENT}% repo + {credit_spread}% credit spread"
        + (f" + {fraud_premium}% fraud premium" if fraud_premium else "")
        + (f" + {news_premium}% adverse-media premium" if news_premium else "")
        + f" = {interest_rate}%. {sizing_basis}"
    )

    result = {
        "probability_of_default": round(float(probability_of_default), 2),
        "probability_of_default_uncalibrated": round(100.0 * raw_probability, 2),
        "recommended_interest_rate": interest_rate,
        "decision": decision,
        "decision_reasons": decision_reasons,
        "recommended_loan_amount": recommended_loan,
        "recommended_loan_basis": sizing_basis,
        "base_risk": base_risk,
        "decision_reasoning": reasoning,
        "shap_chart_path": chart_url,
        "shap_factors": shap_factors,
        "shap_note": (
            "Impacts are in PD percentage points: the change in probability of "
            "default when that feature's contribution is removed. The logistic "
            "link is not linear, so they do not sum exactly to the total."
        ),
        "interest_rate_breakdown": {
            "repo_rate_percent": REPO_RATE_PERCENT,
            "credit_spread_percent": credit_spread,
            "fraud_premium_percent": fraud_premium,
            "adverse_media_premium_percent": news_premium,
            "total_percent": interest_rate,
        },
        "features_used": {
            name: (None if pd.isna(frame.iloc[0][name]) else round(float(frame.iloc[0][name]), 4))
            for name in FEATURES
        },
        "features_not_extracted": missing,
        "feature_completeness_percent": data_completeness,
        "inputs_outside_the_model": {
            "fraud_risk_level": fraud_level,
            "news_risk_score": round(news_score, 1),
            "note": (
                "Neither is a model feature: there is no labelled dataset here to "
                "train them on. They set the premium and the decision band above, "
                "by the stated rules."
            ),
        },
        "model": model_card(),
    }

    cache_set(cache_key, result, 3600)
    return result
