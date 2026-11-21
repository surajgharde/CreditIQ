"""
Underwriting decisions, loan sizing and feature handling in scoring_service.

These pin behaviour that was previously impossible to reach or silently faked:
REJECT (both branches returned CONDITIONAL "to ensure valid processed workflows
pass"), loan sizing (operating cash flow was never extracted and defaulted to
10% of the request, making every recommendation 41.7% of it), and the hardcoded
fallback ratios that let a PD be computed with no financials behind it.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import scoring_service as scoring
from services.credit_features import FEATURES, features_from_financials

HEALTHY = {
    "revenue_fy24": 500_000_000,
    "gross_profit": 150_000_000,
    "ebitda": 90_000_000,
    "ebit": 70_000_000,
    "net_profit": 45_000_000,
    "total_assets": 400_000_000,
    "total_liabilities": 160_000_000,
    "total_equity": 240_000_000,
    "current_assets": 180_000_000,
    "current_liabilities": 90_000_000,
    "inventory": 40_000_000,
    "interest_expense": 12_000_000,
    "operating_cash_flow": 75_000_000,
}


# ---------------------------------------------------------------- decisions


def test_high_fraud_risk_is_rejected():
    decision, reasons = scoring._decide(5.0, "HIGH")
    assert decision == "REJECT"
    assert any("HIGH" in reason for reason in reasons)


def test_pd_above_fifty_percent_is_rejected():
    decision, reasons = scoring._decide(50.1, "LOW")
    assert decision == "REJECT"
    assert any("50" in reason for reason in reasons)


def test_pd_at_the_threshold_is_not_rejected():
    assert scoring._decide(50.0, "LOW")[0] != "REJECT"


@pytest.mark.parametrize("pd_percent,fraud,expected", [
    (5.0, "LOW", "APPROVE"),
    (25.0, "LOW", "APPROVE"),
    (25.1, "LOW", "CONDITIONAL"),
    (5.0, "MEDIUM", "CONDITIONAL"),
    (5.0, "UNKNOWN", "CONDITIONAL"),
    (60.0, "MEDIUM", "REJECT"),
])
def test_decision_bands(pd_percent, fraud, expected):
    assert scoring._decide(pd_percent, fraud)[0] == expected


def test_unperformed_fraud_check_is_not_treated_as_passed():
    # UNKNOWN must cost the same premium as MEDIUM, never LOW's zero.
    assert scoring.FRAUD_PREMIUM["UNKNOWN"] > scoring.FRAUD_PREMIUM["LOW"]


# ------------------------------------------------------------- loan sizing


def test_missing_cash_flow_declines_to_size():
    sized, basis = scoring._size_loan(None, 50_000_000, 10.0)
    assert sized is None
    assert "not extracted" in basis.lower()


def test_negative_cash_flow_sizes_to_zero():
    sized, basis = scoring._size_loan(-5_000_000, 50_000_000, 10.0)
    assert sized == 0.0
    assert "no cash available" in basis.lower()


def test_sizing_uses_cash_flow_and_caps_at_the_request():
    # 10,000,000 of cash flow at a 1.2x floor services 8,333,333 a year, which
    # supports far more than the 1,000,000 requested.
    sized, _ = scoring._size_loan(10_000_000, 1_000_000, 10.0)
    assert sized == 1_000_000


def test_sizing_caps_at_what_cash_flow_supports():
    sized, basis = scoring._size_loan(1_000_000, 500_000_000, 10.0)
    assert sized < 500_000_000
    assert "capped" in basis.lower()
    # 833,333 a year for five years at 10% has a present value near 3.16m.
    assert 3_000_000 < sized < 3_300_000


def test_sizing_is_not_a_fixed_fraction_of_the_request():
    """The old sizing returned 41.7% of the request for every applicant."""
    fractions = {
        round(scoring._size_loan(cash, 100_000_000, 10.0)[0] / 100_000_000, 4)
        for cash in (5_000_000, 20_000_000, 40_000_000)
    }
    assert len(fractions) == 3


def test_annuity_factor_discounts_future_payments():
    # Five annual payments of 1 are worth less than 5 once discounted.
    assert scoring._annuity_factor(10.0, 5) < 5.0
    assert scoring._annuity_factor(0.0, 5) == 5.0


# ---------------------------------------------------------------- features


def test_missing_statement_lines_become_nan_not_defaults():
    values, missing = features_from_financials({"revenue_fy24": 1_000_000})
    assert "current_ratio" in missing
    assert math.isnan(values["current_ratio"])


def test_every_ratio_is_computed_when_every_line_is_present():
    values, missing = features_from_financials(HEALTHY)
    assert missing == []
    assert values["current_ratio"] == pytest.approx(2.0)
    assert values["debt_to_assets"] == pytest.approx(0.4)
    assert values["debt_to_equity"] == pytest.approx(160 / 240)
    assert values["interest_coverage"] == pytest.approx(70 / 12)
    assert values["cash_flow_to_debt"] == pytest.approx(75 / 160)


def test_liabilities_are_derived_from_assets_and_equity_when_absent():
    financials = {k: v for k, v in HEALTHY.items() if k != "total_liabilities"}
    values, _ = features_from_financials(financials)
    assert values["debt_to_assets"] == pytest.approx(0.4)


# ------------------------------------------------------------ end to end


def test_scoring_refuses_when_no_ratio_can_be_computed():
    result = scoring.calculate_credit_score({}, "LOW", 0.0, 1_000_000)
    assert "error" in result
    assert "no probability of default" in result["error"].lower()


def test_scoring_a_healthy_applicant_end_to_end():
    result = scoring.calculate_credit_score(HEALTHY, "LOW", 5.0, 100_000_000)
    assert 0.0 <= result["probability_of_default"] <= 100.0
    assert result["decision"] in ("APPROVE", "CONDITIONAL", "REJECT")
    assert result["features_not_extracted"] == []
    assert result["feature_completeness_percent"] == 100.0
    # The rate is the stated sum of its stated parts.
    breakdown = result["interest_rate_breakdown"]
    assert breakdown["total_percent"] == pytest.approx(
        breakdown["repo_rate_percent"]
        + breakdown["credit_spread_percent"]
        + breakdown["fraud_premium_percent"]
        + breakdown["adverse_media_premium_percent"]
    )
    # Fraud and news are reported as what they are: not model features.
    assert result["inputs_outside_the_model"]["fraud_risk_level"] == "LOW"
    # Every SHAP factor names a real model feature.
    assert {f["feature"] for f in result["shap_factors"]} == set(FEATURES)


def test_high_fraud_rejects_and_sizes_to_zero_end_to_end():
    result = scoring.calculate_credit_score(HEALTHY, "HIGH", 5.0, 100_000_000)
    assert result["decision"] == "REJECT"
    assert result["recommended_loan_amount"] == 0.0


def test_partial_financials_report_what_was_missing():
    partial = {
        "revenue_fy24": 200_000_000,
        "total_assets": 300_000_000,
        "total_liabilities": 120_000_000,
        "total_equity": 180_000_000,
        "current_assets": 90_000_000,
        "current_liabilities": 60_000_000,
    }
    result = scoring.calculate_credit_score(partial, "LOW", 0.0, 50_000_000)
    assert "cash_flow_to_debt" in result["features_not_extracted"]
    assert result["feature_completeness_percent"] < 100.0
    # No cash flow statement means no sized facility.
    assert result["recommended_loan_amount"] is None


def test_model_card_reports_held_out_metrics():
    card = scoring.model_card()
    assert card["available"] is True
    assert card["held_out"]["roc_auc"] > 0.5
    assert card["held_out"]["ks"] > 0.0
    assert "bankruptcy" in card["dataset"]["name"].lower()
