/**
 * FILE 4 — fraudApi.ts
 * GST mismatch, circular trading graph, MCA X-Ray.
 */
import api from './apiConfig';

export interface GSTDetector {
  gstr_2a_amount: number;
  gstr_3b_amount: number;
  mismatch_amount: number;
  confidence_score: number;
  risk_level: string;
  finding: string;
  research_source: string;
}

export interface CircularEntity {
  company_name: string;
  gstin: string;
  amount_sent: number;
  amount_received: number;
}

export interface CircularTrading {
  detected: boolean;
  entities_involved: number;
  total_amount_rotated: number;
  entities: CircularEntity[];
  graph_data: {
    nodes: { id: number; label: string; color: string }[];
    edges: { from: number; to: number; label: string }[];
  };
}

export interface MCACompany {
  company_name: string;
  role: string;
  period_from: string;
  period_to: string;
  defaulted: boolean;
  default_amount: number;
  default_year: string;
}

export interface MCAXRay {
  promoter_name: string;
  din_number: string;
  disqualified: boolean;
  disqualification_reason: string;
  past_companies: MCACompany[];
  risk_level: string;
}

export interface FraudResults {
  gst_detector: GSTDetector;
  circular_trading: CircularTrading;
  mca_xray: MCAXRay;
  overall_verdict: {
    risk_level: string;
    signals_count: number;
    recommendation: string;
  };
}

/** Fetch all fraud analysis results */
export async function getFraudResults(analysisId: number): Promise<FraudResults> {
  const res = await api.get<FraudResults>(`/api/fraud/${analysisId}`);
  return res.data;
}

/**
 * Returns the URL of the PyVis HTML circular trading graph.
 * Embed this in an <iframe src={url} /> to show the interactive graph.
 */
export function getCircularTradingGraphUrl(analysisId: number): string {
  return `${window.location.origin}/api/fraud/graph/${analysisId}`;
}

/**
 * Fetch the raw PyVis HTML string directly (alternative to iframe URL).
 * Use dangerouslySetInnerHTML in a sandboxed div.
 */
export async function getCircularTradingGraph(analysisId: number): Promise<string> {
  const res = await api.get<string>(`/api/fraud/graph/${analysisId}`, {
    responseType: 'text',
    headers: { Accept: 'text/html' },
  });
  return res.data as unknown as string;
}
