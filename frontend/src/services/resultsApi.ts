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
    /** null when cash flow from operations was not extracted, so the facility could not be sized. */
    recommended_loan_amount: number | null;
    recommended_interest_rate: number;
    probability_of_default: number;
    data_quality_score: number;
  };
  fraud: {
    /** HIGH | MEDIUM | LOW | UNKNOWN — UNKNOWN means the checks could not run. */
    overall_fraud_risk: string;
    total_signals_found: number;
    signals: FraudSignal[];
  };
  shap: {
    shap_chart_url: string;
    shap_factors: SHAPFactor[];
    /** The model's base default rate, or null when no model output was recorded. */
    base_risk: number | null;
    final_pd: number | null;
    /** How to read the impact figures; they are not exactly additive. */
    note?: string | null;
  };
  news: {
    news_risk_score: number;
    top_signals: NewsSignal[];
    /** false when no coverage was found at all, so the score is 0 for lack of data. */
    news_data_available?: boolean;
  };
  recommendation: {
    decision_reasoning: string;
    decision_reasons?: string[];
    conditions: string[];
    loan_tenure: number;
    recommended_loan_basis?: string | null;
    interest_rate_breakdown: string;
  };
  /** Provenance and held-out metrics of the model that produced the PD. */
  model?: {
    available?: boolean;
    trained_at?: string | null;
    held_out?: { roc_auc?: number; ks?: number };
    dataset?: { name?: string; url?: string };
  };
  /** Ratios the document reader could not compute, by feature name. */
  features_not_extracted?: string[];
  feature_completeness_percent?: number | null;
  /** true when demo mode generated one or more of the fraud signals. */
  fraud_data_synthetic?: boolean;
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
