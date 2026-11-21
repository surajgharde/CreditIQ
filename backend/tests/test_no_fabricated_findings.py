"""
The rule these tests exist to enforce: the system never invents a finding about
a company.

Three things used to break it. The fraud engine generated GST mismatches, a
planted circular-trading loop and director defaults whenever real data was
missing, and reported them as real. The news engine invented headlines about the
named company ("CFO exits <company> amid internal restructuring") when scraping
found nothing, and scored them. The scorer added a flat +12.5 to every
company's news score from a function that only returned constants.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import fraud_service

GSTIN = "29ABCDE1234F1Z5"
CIN = "U12345MH2001PTC123456"


# --------------------------------------------------------- demo mode is off


def test_demo_mode_is_off_unless_the_environment_says_otherwise(monkeypatch):
    monkeypatch.delenv("CREDITIQ_DEMO_MODE", raising=False)
    assert fraud_service.demo_mode_enabled() is False


def test_demo_mode_only_accepts_affirmative_values(monkeypatch):
    for value in ("", "false", "no", "0", "off"):
        monkeypatch.setenv("CREDITIQ_DEMO_MODE", value)
        assert fraud_service.demo_mode_enabled() is False
    for value in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv("CREDITIQ_DEMO_MODE", value)
        assert fraud_service.demo_mode_enabled() is True


# ------------------------------------------- no data, no generated findings


def test_without_data_every_check_reports_unknown(monkeypatch):
    monkeypatch.setenv("CREDITIQ_DEMO_MODE", "false")
    # No GSTN credentials configured in the test environment, so the GST check
    # has neither documents nor an API.
    result = fraud_service.run_fraud_detection(GSTIN, CIN, dins=None, gst_data=None, trx_data=None)

    assert result["fraud_data_synthetic"] is False
    assert result["demo_mode"] is False
    assert result["checks_run"] == 0
    assert result["fraud_risk_level"] == "UNKNOWN"
    assert result["total_evidence_amount"] == 0.0

    for signal in result["signals"]:
        assert signal["risk_level"] == "UNKNOWN", signal["signal_type"]
        assert signal["confidence_score"] == 0.0, signal["signal_type"]
        assert signal["data_available"] is False, signal["signal_type"]
        assert signal["synthetic"] is False, signal["signal_type"]


def test_an_unrun_check_never_reports_good(monkeypatch):
    """A check that did not run is not a check that passed."""
    monkeypatch.setenv("CREDITIQ_DEMO_MODE", "false")
    result = fraud_service.run_fraud_detection(GSTIN, CIN)
    assert all(s["risk_level"] != "GOOD" for s in result["signals"])


def test_no_findings_are_generated_without_data(monkeypatch):
    monkeypatch.setenv("CREDITIQ_DEMO_MODE", "false")
    result = fraud_service.run_fraud_detection(GSTIN, CIN)
    joined = " ".join(s["description"] for s in result["signals"]).lower()
    # None of the generated shapes may appear.
    for invented in ("shell_company", "tesseract logistics", "suspended entity", "disqualified"):
        assert invented not in joined


def test_missing_dins_do_not_become_a_director_screening_result():
    unavailable = fraud_service.analyze_mca_directors([])
    assert unavailable["risk_level"] == "UNKNOWN"
    assert unavailable["confidence_score"] == 0.0


# ----------------------------------------- demo mode marks everything it makes


def test_demo_mode_marks_every_generated_signal(monkeypatch):
    monkeypatch.setenv("CREDITIQ_DEMO_MODE", "true")
    result = fraud_service.run_fraud_detection(
        GSTIN, CIN, dins=None, gst_data=None, trx_data=None, ocr_revenue=120_000_000
    )

    assert result["demo_mode"] is True
    assert result["fraud_data_synthetic"] is True
    assert set(result["synthetic_signal_types"]) == {
        "GST_MISMATCH", "CIRCULAR_TRADING", "MCA_DIRECTOR"
    }

    for signal in result["signals"]:
        assert signal["synthetic"] is True, signal["signal_type"]
        assert signal["description"].startswith(fraud_service.SYNTHETIC_PREFIX)
        assert "SYNTHETIC" in signal["description"]


def test_a_generated_signal_never_sets_the_overall_risk_level(monkeypatch):
    """The overall level drives the decision and the price, so only real
    findings may move it."""
    monkeypatch.setenv("CREDITIQ_DEMO_MODE", "true")
    result = fraud_service.run_fraud_detection(GSTIN, CIN, ocr_revenue=120_000_000)
    assert result["checks_run"] == 0
    assert result["fraud_risk_level"] == "UNKNOWN"


def test_real_data_is_analysed_and_not_marked_synthetic(monkeypatch):
    monkeypatch.setenv("CREDITIQ_DEMO_MODE", "false")
    gst = [
        {"month": "Jan", "gstr_2a": 1_000_000, "gstr_3b": 1_000_000, "filed_on_time": True},
        {"month": "Feb", "gstr_2a": 1_000_000, "gstr_3b": 1_000_000, "filed_on_time": True},
    ]
    ledger = [
        {"from_node": GSTIN, "to_node": "A", "amount": 500_000},
        {"from_node": "A", "to_node": "B", "amount": 500_000},
        {"from_node": "B", "to_node": GSTIN, "amount": 500_000},
    ]
    result = fraud_service.run_fraud_detection(GSTIN, CIN, gst_data=gst, trx_data=ledger)

    gst_signal = next(s for s in result["signals"] if s["signal_type"] == "GST_MISMATCH")
    circ_signal = next(s for s in result["signals"] if s["signal_type"] == "CIRCULAR_TRADING")

    assert gst_signal["synthetic"] is False
    assert gst_signal["risk_level"] == "GOOD"  # the figures match exactly
    # An exact-value three-hop loop is a real detection on real input.
    assert circ_signal["risk_level"] == "HIGH"
    assert circ_signal["synthetic"] is False
    assert result["fraud_risk_level"] == "HIGH"
    assert result["checks_run"] == 2


# --------------------------------------------------- the removed generators


def test_the_news_fallback_generator_is_gone():
    import services.rag_service as rag
    assert not hasattr(rag, "_generate_fallback_articles")


def test_no_coverage_is_reported_as_no_coverage():
    import services.rag_service as rag
    empty = rag._no_coverage_result("Some Company Private Limited", 4)
    assert empty["news_risk_score"] == 0.0
    assert empty["signals"] == []
    assert empty["news_data_available"] is False
    assert "no news coverage was found" in empty["note"].lower()


def test_the_hardcoded_rag_score_modifier_is_gone():
    import services.scoring_service as scoring
    assert not hasattr(scoring, "get_chromadb_context")
    source = open(scoring.__file__, encoding="utf-8").read()
    assert "12.5" not in source


def test_chromadb_retrieval_is_a_real_query_or_says_it_is_unavailable():
    import services.rag_service as rag
    retrieved = rag.query_news_context("Some Company", "adverse media")
    assert set(retrieved) >= {"available", "documents"}
    if not retrieved["available"]:
        assert retrieved["reason"]
