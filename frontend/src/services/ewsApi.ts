/**
 * FILE 6 — ewsApi.ts
 * Early Warning System — signals, alerts, acknowledge, portfolio overview.
 */
import api from './apiConfig';

export interface EWSSignal {
  signal_name: string;
  score: number;
  risk_level: string;
  detail: string;
  source: string;
  last_updated: string;
}

export interface EWSAlert {
  alert_id: number;
  severity: string;
  message: string;
  source: string;
  timestamp: string;
  channels_used: string[];
  acknowledged: boolean;
}

export interface TrajectoryPoint {
  month: string;
  year: string;
  probability_of_default: number;
  is_predicted: boolean;
}

export interface EWSData {
  company_info: {
    company_name: string;
    loan_amount_disbursed: number;
    disbursement_date: string;
    loan_tenure_years: number;
    relationship_manager_name: string;
  };
  trajectory: {
    data_points: TrajectoryPoint[];
    alert_threshold: number;
    alert_triggered: boolean;
    alert_trigger_month: string;
    current_pd: number;
  };
  signals: EWSSignal[];
  alerts_sent: EWSAlert[];
  summary: {
    overall_ews_score: number;
    risk_trend: string;
    recommended_action: string;
    days_since_disbursement: number;
  };
}

export interface LoanPortfolioItem {
  company_id: number;
  company_name: string;
  active_alerts: number;
  monitoring_status: string;
}

export interface AllLoansData {
  total_monitored: number;
  total_active_alerts: number;
  portfolio: LoanPortfolioItem[];
}

/** Fetch complete EWS dashboard for a company */
export async function getEWSData(companyId: number): Promise<EWSData> {
  const res = await api.get<EWSData>(`/api/ews/${companyId}`);
  return res.data;
}

/** Acknowledge a specific alert — marks it as reviewed */
export async function acknowledgeAlert(alertId: number): Promise<{ success: boolean; message: string }> {
  const res = await api.post(`/api/ews/acknowledge/${alertId}`);
  return res.data;
}

/** Get portfolio overview — all monitored loans and their alert counts */
export async function getAllLoans(): Promise<AllLoansData> {
  const res = await api.get<AllLoansData>('/api/ews/all-loans');
  return res.data;
}
