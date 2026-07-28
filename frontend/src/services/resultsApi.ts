/**
 * FILE 3 — resultsApi.ts
 * Full Dashboard results — all numbers come from real backend response.
 */
import api from './apiConfig';

export interface SHAPFactor  { name: string; impact: string; }
export interface NewsSignal  { source: string; date: string; description: string; }
export interface FraudSignal { type: string; risk_level: string; description: string; evidence_amount: number; confidence_score: number; source: string; }

export interface FullResults {
  company: {
    company_name: string;
    cin_number: string;
    gstin_number: string;
    loan_amount_requested: number;
  };
  decision: {
    decision: string;
    recommended_loan_amount: number;
    recommended_interest_rate: number;
    probability_of_default: number;
    data_quality_score: number;
  };
  fraud: {
    overall_fraud_risk: string;
    total_signals_found: number;
    signals: FraudSignal[];
  };
  shap: {
    shap_chart_url: string;
    shap_factors: SHAPFactor[];
    base_risk: number;
    final_pd: number;
  };
  news: {
    news_risk_score: number;
    top_signals: NewsSignal[];
  };
  recommendation: {
    decision_reasoning: string;
    conditions: string[];
    loan_tenure: number;
    interest_rate_breakdown: string;
  };
}

/** Fetch full dashboard results from real DB-backed analysis */
export async function getFullResults(analysisId: number): Promise<FullResults> {
  const res = await api.get<FullResults>(`/api/results/${analysisId}`);
  return res.data;
}

/**
 * Returns the absolute URL for the SHAP chart PNG image.
 * The <img> tag can use this directly as src.
 */
export function getSHAPChartUrl(analysisId: number): string {
  return `${window.location.origin}/api/shap-chart/${analysisId}`;
}
