import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.cam_service import generate_cam

# TCS - APPROVE
analysis_tcs = {
    "company": {"company_name": "Tata Consultancy Services Limited", "cin": "U22210MH1995PLC084781", "pan": "AAACB1234M", "loan_amount_requested": 30000000},
    "fraud": {"overall_fraud_risk": "LOW", "signals": []},
    "news": {"news_risk_score": 15, "top_signals": []},
    "shap": {"shap_chart_url": "", "shap_factors": [{"name": "Stable Cash Flow", "impact": "-1.5"}]},
    "decision": {"probability_of_default": 12.5, "data_quality_score": 95, "decision": "APPROVE", "decision_reasoning": "Strong financial stability", "conditions": [], "recommended_loan_amount": 30000000, "recommended_interest_rate": 10.5}
}

# Tech Mahindra - REJECT
analysis_techm = {
    "company": {"company_name": "Tech Mahindra Limited", "cin": "U72100MH1986PLC041370", "pan": "AAACM5678L", "loan_amount_requested": 0},
    "fraud": {"overall_fraud_risk": "HIGH", "signals": [{"signal_type": "GST", "evidence_amount": 7000000}]},
    "news": {"news_risk_score": 80, "top_signals": []},
    "shap": {"shap_chart_url": "", "shap_factors": [{"name": "GST Mismatch", "impact": "+40.5"}]},
    "decision": {"probability_of_default": 85.2, "data_quality_score": 88, "decision": "REJECT", "decision_reasoning": "Suspicious transactions", "conditions": [], "recommended_loan_amount": 0, "recommended_interest_rate": 0}
}

# Infosys - CONDITIONAL
analysis_infosys = {
    "company": {"company_name": "Infosys Limited", "cin": "L85110KA1981PLC013115", "pan": "AAACI6789N", "loan_amount_requested": 20000000},
    "fraud": {"overall_fraud_risk": "MEDIUM", "signals": []},
    "news": {"news_risk_score": 40, "top_signals": []},
    "shap": {"shap_chart_url": "", "shap_factors": [{"name": "Moderate Cash Flow Risk", "impact": "+10.4"}]},
    "decision": {"probability_of_default": 25.4, "data_quality_score": 90, "decision": "CONDITIONAL", "decision_reasoning": "Requires verification", "conditions": [], "recommended_loan_amount": 20000000, "recommended_interest_rate": 12.5}
}

print("Generating TCS CAM...")
generate_cam(analysis_tcs)
print("Generating Tech Mahindra CAM...")
generate_cam(analysis_techm)
print("Generating Infosys CAM...")
generate_cam(analysis_infosys)
print("Done!")
