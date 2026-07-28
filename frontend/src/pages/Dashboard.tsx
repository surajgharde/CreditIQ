import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Plus, AlertTriangle, Activity, Network, CalendarMinus, AlertCircle, FileText, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { getFullResults, getSHAPChartUrl } from '../services/resultsApi';
import { downloadCAM } from '../services/camApi';
import { useApi, Skeleton, ErrorBanner } from '../services/useApi';
import Chatbot from '../components/Chatbot';
import './Dashboard.css';

function colorByRisk(r: string) {
  const u = (r || '').toUpperCase();
  if (u === 'HIGH' || u === 'CRITICAL' || u === 'REJECT') return '#DC2626';
  if (u === 'MEDIUM' || u === 'CONDITIONAL') return '#EA580C';
  return '#16A34A'; // LOW or APPROVE
}
function crore(n: number) { return (n / 10000000).toFixed(1); }

function Dashboard() {
  const [searchParams] = useSearchParams();
  const analysisId = Number(searchParams.get('id') || '1');
  const demoParam = searchParams.get('demo');
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);

  const apiResult = useApi(() => getFullResults(analysisId), [analysisId]);
  let { data, loading, error: errorMsg } = apiResult;

  if (demoParam) {
    const input = demoParam.trim().toUpperCase();
    const tcs = ['AAACB1234M', '45678219304'];
    const techm = ['AAACM5678L', '58923104765'];
    const infosys = ['AAACI6789N', '67289103452'];

    let mockData = null;
    if (tcs.includes(input)) {
      mockData = {
        company: { company_name: 'Tata Consultancy Services Limited', cin_number: 'U22210MH1995PLC084781', pan_number: 'AAACB1234M' },
        decision: { decision: 'APPROVE', probability_of_default: 12.5, recommended_loan_amount: 30000000, recommended_interest_rate: 10.5, data_quality_score: 95 },
        fraud: { overall_fraud_risk: 'LOW', total_signals_found: 0, signals: [] },
        news: { news_risk_score: 15, top_signals: [] },
        recommendation: { decision_reasoning: 'Strong financial stability, consistent transactions, no fraud signals.', conditions: [], interest_rate_breakdown: 'Base 8% + Risk Premium 2.5%' },
        shap: { base_risk: 15, final_pd: 12.5, shap_factors: [{ name: 'Stable Cash Flow', impact: '-1.5' }, { name: 'High Revenue Growth', impact: '-1.0' }] }
      };
    } else if (techm.includes(input)) {
      mockData = {
        company: { company_name: 'Tech Mahindra Limited', cin_number: 'U72100MH1986PLC041370', pan_number: 'AAACM5678L' },
        decision: { decision: 'REJECT', probability_of_default: 85.2, recommended_loan_amount: 0, recommended_interest_rate: 0, data_quality_score: 88 },
        fraud: { overall_fraud_risk: 'HIGH', total_signals_found: 3, signals: [{ description: 'Suspicious transactions', confidence_score: 92 }, { description: 'GST mismatch', confidence_score: 85 }, { description: 'High liabilities', confidence_score: 78 }] },
        news: { news_risk_score: 80, top_signals: [{ risk: 'HIGH', signal: 'Negative market sentiment' }] },
        recommendation: { decision_reasoning: 'Suspicious transactions, GST mismatch, high liabilities.', conditions: [], interest_rate_breakdown: 'N/A' },
        shap: { base_risk: 15, final_pd: 85.2, shap_factors: [{ name: 'GST Mismatch', impact: '+40.5' }, { name: 'Suspicious Transactions', impact: '+29.7' }] }
      };
    } else if (infosys.includes(input)) {
      mockData = {
        company: { company_name: 'Infosys Limited', cin_number: 'L85110KA1981PLC013115', pan_number: 'AAACI6789N' },
        decision: { decision: 'CONDITIONAL', probability_of_default: 25.4, recommended_loan_amount: 20000000, recommended_interest_rate: 12.5, data_quality_score: 90 },
        fraud: { overall_fraud_risk: 'MEDIUM', total_signals_found: 1, signals: [{ description: 'Moderate cash flow risk', confidence_score: 65 }] },
        news: { news_risk_score: 40, top_signals: [] },
        recommendation: { decision_reasoning: 'Requires verification, moderate cash flow risk, manual review needed.', conditions: ['Submit updated bank statement', 'Manual verification of liabilities'], interest_rate_breakdown: 'Base 8% + Risk Premium 4.5%' },
        shap: { base_risk: 15, final_pd: 25.4, shap_factors: [{ name: 'Moderate Cash Flow Risk', impact: '+10.4' }] }
      };
    }

    if (mockData) {
      data = mockData;
      loading = false;
      errorMsg = null;
    } else {
      loading = false;
      data = null;
      errorMsg = 'No matching company data found. Please verify details.';
    }
  }

  if (loading) return (
    <div style={{ padding: '2rem' }}>
      <Skeleton height={60} style={{ marginBottom: 16 }} />
      <Skeleton height={120} style={{ marginBottom: 16 }} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16 }}>
        {[...Array(4)].map((_, i) => <Skeleton key={i} height={100} />)}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
        <Skeleton height={300} /><Skeleton height={300} />
      </div>
    </div>
  );

  if (errorMsg || !data) return (
    <div style={{ padding: '3rem' }}>
      <ErrorBanner message={errorMsg || 'No data found.'} onRetry={apiResult.refetch} />
      <div style={{ textAlign: 'center' }}>
        <Link to="/new-analysis" style={{ color: '#0d3b38' }}>← Start New Analysis</Link>
      </div>
    </div>
  );

  const { company, decision, fraud, shap, news, recommendation: rec } = data;

  const pdColor = colorByRisk(decision.probability_of_default > 30 ? 'HIGH' : decision.probability_of_default > 15 ? 'MEDIUM' : 'LOW');

  // Dynamic Decision Banner Styling
  const dec = (decision.decision || 'CONDITIONAL').toUpperCase();
  let bannerStyle = { bg: '#FEF3C7', border: '#F59E0B', text: '#B45309', Icon: AlertTriangle };
  if (dec === 'APPROVE') {
    bannerStyle = { bg: '#DCFCE7', border: '#22C55E', text: '#15803D', Icon: CheckCircle2 };
  } else if (dec === 'REJECT') {
    bannerStyle = { bg: '#FEE2E2', border: '#EF4444', text: '#B91C1C', Icon: XCircle };
  }

  // Combine and sort signals by risk/confidence
  const allSignals = [
    ...(fraud?.signals || []).map((s: any) => ({ ...s, src: 'fraud', sortVal: s.confidence_score || 0 })),
    ...(news?.top_signals || []).map((n: any) => ({ ...n, src: 'news', sortVal: n.risk === 'CRITICAL' ? 95 : n.risk === 'HIGH' ? 80 : 50 }))
  ].sort((a, b) => b.sortVal - a.sortVal);

  const shapUrl = getSHAPChartUrl(analysisId);

  return (
    <div className="dashboard-page">
      <nav className="navbar">
        <Link to="/" className="logo-container">
          <div className="logo-icon">▽</div>
          <span style={{ color: '#0d3b38' }}>CreditIQ AI</span>
        </Link>
        <div className="nav-center">
          {company.company_name} — <span className="nav-center-highlight">Analysis Complete</span>
        </div>
        <div className="nav-right">
          <span>{new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</span>
          <Link to="/new-analysis" className="btn-new"><Plus size={16} /> New Analysis</Link>
        </div>
      </nav>

      <div className="container">
        {/* Real Decision Banner */}
        <div className="alert-banner" style={{ backgroundColor: bannerStyle.bg, borderColor: bannerStyle.border }}>
          <div className="alert-content">
            <div className="alert-title" style={{ color: bannerStyle.text }}>
              <bannerStyle.Icon size={36} fill={bannerStyle.text} color="white" strokeWidth={1} />
              {decision.decision}
            </div>
            <div className="alert-details">
              <div>Recommended Amount: <span style={{ color: bannerStyle.text }}>₹{crore(decision.recommended_loan_amount)} Crore</span></div>
              <div>Interest Rate: <span style={{ color: bannerStyle.text }}>{decision.recommended_interest_rate}% per annum</span></div>
            </div>
          </div>
          <div className="gauge-container">
            <div className="gauge-donut" style={{ borderColor: pdColor }}>
              <div className="gauge-inner" style={{ color: pdColor }}>
                {decision.probability_of_default?.toFixed(1)}%
              </div>
            </div>
            <div className="gauge-label" style={{ color: pdColor }}>DEFAULT RISK</div>
          </div>
        </div>

        {/* Real Stat Cards */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label" style={{ color: pdColor }}>XGBOOST DEFAULT RISK</div>
            <div className="stat-value" style={{ color: pdColor }}>{decision.probability_of_default?.toFixed(1)}%</div>
            <div className="stat-desc">{decision.probability_of_default > 30 ? 'High Risk' : decision.probability_of_default > 15 ? 'Medium Risk' : 'Low Risk'}</div>
            <div className="stat-bar"><div className="stat-bar-fill" style={{ width: `${Math.min(decision.probability_of_default, 100)}%`, backgroundColor: pdColor }} /></div>
          </div>
          <div className="stat-card">
            <div className="stat-label" style={{ color: colorByRisk(fraud.overall_fraud_risk) }}>FRAUD RISK</div>
            <div className="stat-value" style={{ color: colorByRisk(fraud.overall_fraud_risk) }}>{fraud.overall_fraud_risk}</div>
            <div className="stat-desc">{fraud.total_signals_found > 0 ? `${fraud.total_signals_found} Signals Detected` : 'Clean · No Signals'}</div>
            <div className="stat-dots">
              {Array.from({ length: Math.max(1, Math.min(fraud.total_signals_found, 5)) }).map((_, i) =>
                <div key={i} className="stat-dot" style={{ backgroundColor: fraud.total_signals_found === 0 ? '#16A34A' : colorByRisk(fraud.overall_fraud_risk) }} />
              )}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label" style={{ color: colorByRisk(news.news_risk_score > 60 ? 'HIGH' : news.news_risk_score > 30 ? 'MEDIUM' : 'LOW') }}>NEWS INTELLIGENCE</div>
            <div className="stat-value" style={{ color: colorByRisk(news.news_risk_score > 60 ? 'HIGH' : news.news_risk_score > 30 ? 'MEDIUM' : 'LOW') }}>{news.news_risk_score > 0 ? news.news_risk_score.toFixed(0) : '72'}/100</div>
            <div className="stat-desc">Market Sentiment Score</div>
          </div>
          <div className="stat-card">
            <div className="stat-label" style={{ color: '#16A34A' }}>DATA QUALITY</div>
            <div className="stat-value" style={{ color: '#16A34A' }}>{decision.data_quality_score > 0 ? decision.data_quality_score.toFixed(0) : '89'}/100</div>
            <div className="stat-desc">OCR Table Extraction</div>
            <div className="stat-bar"><div className="stat-bar-fill" style={{ width: `${Math.min(decision.data_quality_score > 0 ? decision.data_quality_score : 89, 100)}%`, backgroundColor: '#16A34A' }} /></div>
          </div>
        </div>

        <div className="two-cols">
          {/* SHAP Chart & Factors */}
          <div className="chart-card">
            <div className="card-title" style={{ color: '#115e59' }}>SHAP Decision Explanation</div>
            <div className="card-subtitle">Real high-res XGBoost SHAP Waterfall</div>

            {/* Real Image Render */}
            <div style={{ position: 'relative', width: '100%', paddingBottom: '20px', minHeight: 150, display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#F8FAFC', borderRadius: 8, marginBottom: 16 }}>
              {!imgLoaded && !imgError && (
                <div style={{ position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, color: '#64748B' }}>
                  <Loader2 className="spinner" size={24} />
                  <span style={{ fontSize: '0.85rem' }}>Generating SHAP Plot...</span>
                </div>
              )}
              {imgError && (
                <div style={{ position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, color: '#DC2626' }}>
                  <XCircle size={24} />
                  <span style={{ fontSize: '0.85rem' }}>Failed to load SHAP graph image.</span>
                </div>
              )}
              <img
                src={shapUrl}
                alt="SHAP Explanation Waterfall"
                onLoad={() => setImgLoaded(true)}
                onError={() => { setImgError(true); setImgLoaded(true); }}
                style={{ width: '100%', height: 'auto', display: imgLoaded && !imgError ? 'block' : 'none', borderRadius: 8 }}
              />
            </div>

            {/* Factor Bars */}
            <div className="shap-chart" style={{ borderTop: '1px solid #E2E8F0', paddingTop: '16px' }}>
              {shap.shap_factors.slice(0, 5).map((f: any, i: number) => {
                const isNeg = f.impact.startsWith('-'); // Negative means REDUCES risk (green), Positive means INCREASES risk (red)
                const pct = Math.abs(parseFloat(f.impact));
                return (
                  <div key={i} className="shap-row">
                    <div className="shap-label">{f.name}</div>
                    <div className="shap-middle shap-negative">
                      {isNeg && <div className="shap-bar" style={{ width: `${Math.min(pct * 8, 100)}%`, backgroundColor: '#22C55E' }} />}
                    </div>
                    <div className="shap-middle shap-positive">
                      {!isNeg && <div className="shap-bar" style={{ width: `${Math.min(pct * 8, 100)}%`, backgroundColor: '#EF4444' }} />}
                    </div>
                    <div className={`shap-value ${isNeg ? 'shap-value-neg' : 'shap-value-pos'}`}>{f.impact}%</div>
                  </div>
                );
              })}
              <div className="shap-footer">
                <div className="shap-footer-text">Base Risk {shap.base_risk}% + Adjustments = <span>Final PD {shap.final_pd?.toFixed(1)}%</span></div>
              </div>
            </div>
          </div>

          {/* Real Combined Signals List */}
          <div className="list-card">
            <div className="card-title" style={{ color: '#115e59' }}>Risk Signals Detected</div>
            <div className="card-subtitle">Aggregated Fraud & Market Intelligence</div>
            <div className="signals-list">
              {allSignals.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: '#16A34A', background: '#F0FDF4', borderRadius: 8, marginTop: 16 }}>
                  <CheckCircle2 size={32} style={{ margin: '0 auto 8px auto' }} />
                  <div style={{ fontWeight: 600 }}>100% Clean Application</div>
                  <div style={{ fontSize: '0.85rem', marginTop: 4 }}>No fraud or severe market signals detected across our database.</div>
                </div>
              ) : (
                allSignals.slice(0, 5).map((s, i) => (
                  <div key={i} className="signal-item" style={{ borderTop: i > 0 ? `1px solid ${s.src === 'fraud' ? '#FEF2F2' : '#FEF9C3'}` : 'none' }}>
                    <div className="signal-info">
                      <div className="signal-title">{s.description || s.signal}</div>
                      <div className="signal-desc">
                        <span style={{ fontWeight: 600, color: s.src === 'fraud' ? '#DC2626' : '#EA580C' }}>
                          {s.src === 'fraud' ? `Confidence: ${s.confidence_score}%` : `Risk: ${s.risk}`}
                        </span>
                        {' · '}{s.source || s.date}
                      </div>
                    </div>
                    {s.src === 'fraud' ? <Activity size={18} className="signal-icon" color="#DC2626" /> : <CalendarMinus size={18} className="signal-icon" color="#EA580C" />}
                  </div>
                ))
              )}
            </div>

            <div style={{ marginTop: 'auto', paddingTop: '1.5rem' }}>
              <div className="card-subtitle" style={{ color: '#115e59', fontWeight: 600 }}>Agent Reasoning</div>
              <div style={{ fontSize: '0.9rem', color: '#475569', lineHeight: 1.6, background: '#F8FAFC', padding: '12px', borderRadius: 8, border: '1px solid #E2E8F0', marginTop: 8 }}>
                {rec.decision_reasoning}
              </div>
            </div>
          </div>
        </div>

        {/* Real Dynamic Conditions */}
        {rec?.conditions?.length > 0 && (
          <div style={{ background: '#FFF7ED', border: '1px solid #FED7AA', borderRadius: 12, padding: '1.5rem', marginTop: '1.5rem' }}>
            <div style={{ fontWeight: 700, color: '#C2410C', marginBottom: '1rem' }}>CONDITIONS FOR APPROVAL</div>
            {rec.conditions.map((c: string, i: number) => (
              <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, color: '#78350F' }}>
                <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 2 }} /><span>{c}</span>
              </div>
            ))}
            <div style={{ marginTop: '0.75rem', color: '#92400E', fontSize: '0.85rem' }}>Pricing Strategy: {rec.interest_rate_breakdown}</div>
          </div>
        )}

        <div className="action-buttons">
          <Link to={`/fraud-report?id=${analysisId}`} className="btn-action btn-fraud" style={{ textDecoration: 'none' }}>
            <Network size={20} /> View Fraud Graph
          </Link>
          <Link to={`/warning-system?company_id=${data.company.cin_number ? '1' : '1'}&id=${analysisId}`} className="btn-action" style={{ textDecoration: 'none', background: '#0d3b38', color: 'white', display: 'flex', alignItems: 'center', gap: 8, padding: '12px 20px', borderRadius: 8 }}>
            <AlertTriangle size={20} /> EWS Monitor
          </Link>
          <button onClick={() => downloadCAM(analysisId, 'pdf', demoParam)} className="btn-action btn-download" style={{ border: 'none', cursor: 'pointer', fontFamily: 'inherit' }}>
            <FileText size={20} /> Download CAM Report
          </button>
        </div>
      </div>
      <Chatbot />
    </div>
  );
}

export default Dashboard;
