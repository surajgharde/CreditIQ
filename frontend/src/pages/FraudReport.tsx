import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, CheckCircle2, Maximize2, X, ShieldAlert, Fingerprint, Database } from 'lucide-react';
import { getFraudResults, getCircularTradingGraphUrl } from '../services/fraudApi';
import { useApi, Skeleton, ErrorBanner } from '../services/useApi';
import './FraudReport.css';

function FraudReport() {
  const [searchParams] = useSearchParams();
  const analysisId = Number(searchParams.get('id') || '1');
  
  const [graphModalOpen, setGraphModalOpen] = useState(false);

  const { data, loading, error, refetch } = useApi(() => getFraudResults(analysisId), [analysisId]);

  function crore(n: number) { return (n / 10000000).toFixed(1); }

  if (loading) return (
    <div style={{ padding: '2rem', maxWidth: '1000px', margin: '0 auto' }}>
      <Skeleton height={80} style={{ marginBottom: 24, borderRadius: 16 }} />
      <Skeleton height={120} style={{ marginBottom: 24, borderRadius: 24 }} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 24 }}>
        {[...Array(3)].map((_, i) => <Skeleton key={i} height={300} style={{ borderRadius: 24 }} />)}
      </div>
    </div>
  );

  if (error || !data) return (
    <div style={{ padding: '3rem' }}>
      <ErrorBanner message={error || 'No fraud data found.'} onRetry={refetch} />
    </div>
  );

  const { gst_detector: gst, circular_trading: ct, mca_xray: mca, overall_verdict: verdict } = data;
  const graphUrl = getCircularTradingGraphUrl(analysisId);

  const isOverallClean = verdict.risk_level === 'LOW' || verdict.risk_level === 'GOOD' || verdict.risk_level === 'CLEAN';
  
  const getBadgeStyle = (level: string) => {
    const l = (level || '').toUpperCase();
    if (l === 'HIGH' || l === 'CRITICAL') return { bg: '#FEE2E2', text: '#B91C1C', border: '#FECACA' };
    if (l === 'MEDIUM') return { bg: '#FFEDD5', text: '#C2410C', border: '#FED7AA' };
    return { bg: '#DCFCE7', text: '#15803D', border: '#BBF7D0' };
  };
  
  const verdictStyle = getBadgeStyle(verdict.risk_level);

  return (
    <div className="fraud-page">
      {/* Full Screen Interactive Graph Modal */}
      {graphModalOpen && (
          <div className="graph-modal-overlay">
            <div className="graph-modal-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ background: '#0d9488', padding: 8, borderRadius: 8 }}><Fingerprint size={20} /></div>
                    <div>
                        <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>Circular Trading Intelligence Network</div>
                        <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>Analysis ID #{analysisId} • Real-time Topology</div>
                    </div>
                </div>
                <button onClick={() => setGraphModalOpen(false)} className="graph-close-btn">
                    Close View <X size={20} />
                </button>
            </div>
            <iframe
                src={graphUrl}
                title="Full Screen Network"
                style={{ flex: 1, width: '100%', border: 'none', backgroundColor: '#F8FAFC' }}
                sandbox="allow-scripts allow-same-origin"
            />
          </div>
      )}

      <nav className="fraud-navbar">
        <Link to={`/dashboard?id=${analysisId}`} className="fraud-back-btn">
          <ArrowLeft size={18} /> <span>Portfolio Dashboard</span>
        </Link>
        <div className="fraud-nav-title">Fraud Intelligence Report</div>
        <div className="fraud-badge" style={{ backgroundColor: verdictStyle.bg, color: verdictStyle.text, border: `1px solid ${verdictStyle.border}` }}>
          {verdict.risk_level} RISK
        </div>
      </nav>

      <div className="fraud-container">
        {/* Overall Verdict Banner */}
        <div className="fraud-verdict-banner" style={{ 
            backgroundColor: isOverallClean ? '#ECFDF5' : '#FEF2F2', 
            border: `1px solid ${isOverallClean ? '#10B98133' : '#EF444433'}`,
            background: isOverallClean 
                ? 'linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)' 
                : 'linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%)'
        }}>
          {isOverallClean 
            ? <div style={{ background: '#10B981', padding: 12, borderRadius: 12, color: 'white' }}><ShieldAlert size={24} /></div>
            : <div style={{ background: '#EF4444', padding: 12, borderRadius: 12, color: 'white' }}><AlertTriangle size={24} /></div>
          }
          <div>
            <div style={{ fontWeight: 800, color: isOverallClean ? '#065F46' : '#991B1B', fontSize: '1.25rem', letterSpacing: '-0.02em' }}>
              {isOverallClean ? "Vetted: Zero Exposure Signals" : `${verdict.signals_count} Critical Anomalies Detected`}
            </div>
            <div style={{ color: isOverallClean ? '#047857' : '#B91C1C', fontSize: '0.95rem', marginTop: 4, fontWeight: 500, opacity: 0.9 }}>
                {verdict.recommendation || "System verified 100% creditworthiness integrity."}
            </div>
          </div>
        </div>

        {/* GST DETECTOR */}
        <div className="fraud-section-card">
          <div className="fraud-section-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ color: '#0d9488' }}><Database size={20} /></div>
                <div className="fraud-section-title">GST Mismatch Intelligence</div>
            </div>
            <div className="fraud-risk-tag" style={{ backgroundColor: getBadgeStyle(gst.risk_level).bg, color: getBadgeStyle(gst.risk_level).text }}>
                {gst.risk_level} RISK
            </div>
          </div>
          
          {gst.risk_level === 'GOOD' || gst.risk_level === 'LOW' ? (
              <div style={{ padding: '1.5rem', background: '#F0FDF4', borderRadius: 16, display: 'flex', gap: 16, alignItems: 'center', border: '1px solid #BBF7D0' }}>
                  <div style={{ background: '#16A34A', color: 'white', padding: 8, borderRadius: '50%' }}><CheckCircle2 size={24} /></div>
                  <div>
                      <div style={{ fontWeight: 700, color: '#166534', fontSize: '1.05rem' }}>Full Reconciliation Success</div>
                      <div style={{ fontSize: '0.9rem', color: '#15803D', marginTop: 2 }}>ITC claims align with GSTR-2A vendor declarations.</div>
                  </div>
              </div>
          ) : (
             <div className="gst-grid">
                <div className="gst-row" style={{ background: '#FEF2F2', border: '1px solid #FEE2E2' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontSize: '0.75rem', color: '#991B1B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Identified Leakage</span>
                        <span style={{ color: '#DC2626', fontWeight: 800, fontSize: '1.5rem' }}>₹{crore(gst.mismatch_amount)} Cr</span>
                    </div>
                    <span className="tag-fraud">FRAUD ALERT</span>
                </div>
                <div style={{ background: '#FFF1F2', border: '1px border-dashed #FDA4AF', padding: '1rem', borderRadius: 12, display: 'flex', gap: 12 }}>
                    <AlertTriangle size={20} color="#DC2626" style={{ flexShrink: 0 }} />
                    <span style={{ fontSize: '0.95rem', color: '#9F1239', lineHeight: 1.5 }}>
                        <strong>Forensic Finding:</strong> {gst.finding}
                    </span>
                </div>
             </div>
          )}

          <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: 1.5, display: 'flex', justifyContent: 'space-between' }}>
            <span>Source: <strong>{gst.research_source}</strong></span>
            <span>Confidence Index: <strong>{gst.confidence_score}%</strong></span>
          </div>
        </div>

        {/* CIRCULAR TRADING */}
        <div className="fraud-section-card">
          <div className="fraud-section-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ color: '#0d9488' }}><Fingerprint size={20} /></div>
                <div className="fraud-section-title">Circular Trading Topology</div>
            </div>
            <div className="fraud-risk-tag" style={{ backgroundColor: getBadgeStyle(ct.detected ? 'HIGH' : 'GOOD').bg, color: getBadgeStyle(ct.detected ? 'HIGH' : 'GOOD').text }}>
                {ct.detected ? 'HIGH RISK' : 'CLEAN'}
            </div>
          </div>
          
          <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ maxWidth: '70%', lineHeight: 1.5 }}>
                {ct.detected ? (
                    <div style={{ color: '#991B1B', fontWeight: 500 }}>
                        <strong style={{ fontSize: '1.1rem' }}>{ct.entities_involved} connected nodes</strong> identified rotating <strong style={{ color: '#DC2626' }}>₹{crore(ct.total_amount_rotated)} Crore</strong> in a closed value loop.
                    </div>
                ) : (
                    <div style={{ color: '#166534', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <CheckCircle2 size={18} /> No cyclic fund flows detected across the transactional graph.
                    </div>
                )}
            </div>
            <button onClick={() => setGraphModalOpen(true)} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', padding: '10px 16px', background: '#0d9488', color: 'white', border: 'none', borderRadius: 12, cursor: 'pointer', fontWeight: 600, boxShadow: '0 4px 6px -1px rgba(13, 148, 136, 0.2)' }}>
                <Maximize2 size={16} /> Interactive View
            </button>
          </div>
          
          <div style={{ position: 'relative', height: 400, borderRadius: 20, overflow: 'hidden', border: '1px solid #E2E8F0' }}>
            <iframe
                src={graphUrl}
                title="Circular Trading Network"
                style={{ width: '100%', height: '100%', border: 'none' }}
                sandbox="allow-scripts allow-same-origin"
            />
          </div>
        </div>

        {/* MCA X-RAY */}
        <div className="fraud-section-card" style={{ background: 'linear-gradient(to bottom, #FFFFFF, #F8FAFC)' }}>
          <div className="fraud-section-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ color: '#0d9488' }}><ShieldAlert size={20} /></div>
                <div className="fraud-section-title">MCA Director Portfolio Review</div>
            </div>
            <div className="fraud-risk-tag" style={{ backgroundColor: getBadgeStyle(mca.risk_level).bg, color: getBadgeStyle(mca.risk_level).text }}>
                {mca.risk_level} RISK
            </div>
          </div>
          
          {mca.risk_level === 'GOOD' || mca.risk_level === 'LOW' ? (
              <div style={{ background: '#ECFDF5', border: '1px solid #BBF7D0', padding: '1.5rem', borderRadius: 16, display: 'flex', gap: 16 }}>
                  <div style={{ background: '#10B981', color: 'white', padding: 8, borderRadius: 12, height: 'fit-content' }}><CheckCircle2 size={24} /></div>
                  <div>
                      <div style={{ fontWeight: 700, color: '#065F46', fontSize: '1.1rem' }}>Pristine Promoter History</div>
                      <div style={{ fontSize: '0.95rem', color: '#047857', marginTop: 4 }}>Full cross-entity audit shows zero disqualified status or historical debt defaults.</div>
                  </div>
              </div>
          ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {mca.disqualified && (
                    <div style={{ background: '#EF4444', color: 'white', padding: '1rem 1.5rem', borderRadius: 12, fontWeight: 700, display: 'flex', gap: 12, alignItems: 'center' }}>
                      <ShieldAlert size={20} /> {mca.disqualification_reason || "Director is Disqualified under Sec 164(2)"}
                    </div>
                  )}
                  {mca.past_companies && mca.past_companies.length > 0 ? mca.past_companies.map((c: any, i: number) => (
                    <div key={i} className="mca-item">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div>
                              <div style={{ fontWeight: 800, color: '#0F172A', fontSize: '1.1rem' }}>{c.company_name}</div>
                              <div style={{ fontSize: '0.85rem', color: '#64748B', marginTop: 4 }}>Role: <strong>{c.role}</strong> • {c.period_from} → {c.period_to}</div>
                          </div>
                          {c.defaulted && <div style={{ background: '#FEE2E2', color: '#B91C1C', padding: '4px 10px', borderRadius: 6, fontSize: '0.7rem', fontWeight: 800 }}>ASSOCIATED DEFAULT</div>}
                      </div>
                      {c.defaulted && (
                        <div style={{ background: '#FEF2F2', borderLeft: '4px solid #EF4444', padding: '12px', marginTop: 12, borderRadius: '0 8px 8px 0' }}>
                           <span style={{ fontSize: '0.85rem', color: '#7F1D1D' }}>Legacy default of <strong style={{ fontSize: '1.1rem' }}>₹{crore(c.default_amount)} Cr</strong> detected in FY{c.default_year}.</span>
                        </div>
                      )}
                    </div>
                  )) : (
                    <div style={{ color: '#64748B', fontStyle: 'italic', textAlign: 'center', padding: '2rem' }}>
                        No associated corporate footprints found for provided DINs.
                    </div>
                  )}
              </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default FraudReport;
