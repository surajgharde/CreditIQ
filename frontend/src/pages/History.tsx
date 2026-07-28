import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
    Clock, Zap, FileText, Activity, ShieldAlert, ArrowRight,
    Search, Filter, X, ChevronDown, AlertTriangle,
    CheckCircle, Loader, TrendingUp, Building2, Calendar
} from 'lucide-react';
import './History.css';
import api from '../services/apiConfig';
import { getFullResults } from '../services/resultsApi';
import type { FullResults } from '../services/resultsApi';

interface HistoryRecord {
    analysis_id: number;
    company_name: string;
    gstin_number?: string;
    cin_number?: string;
    loan_amount_requested?: number;
    decision?: string;
    status: string;
    fraud_risk_level?: string;
    probability_of_default?: number;
    news_risk_score?: number;
    cam_status?: string;
    created_at: string;
    failure_reason?: string;
    analyst?: string;
}

function History({ hideNavbar = false }: { hideNavbar?: boolean }) {
    const [history, setHistory] = useState<HistoryRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // filters
    const [search, setSearch] = useState('');
    const [filterRisk, setFilterRisk] = useState('ALL');
    const [filterDecision, setFilterDecision] = useState('ALL');
    const [filterFraud, setFilterFraud] = useState('ALL');

    // detail modal
    const [modal, setModal] = useState<{ open: boolean; record: HistoryRecord | null; details: FullResults | null; detailLoading: boolean }>({
        open: false, record: null, details: null, detailLoading: false
    });

    useEffect(() => {
        let isMounted = true;
        api.get('/api/history')
            .then(res => {
                if (isMounted) {
                    setHistory(Array.isArray(res.data) ? res.data : []);
                    setLoading(false);
                }
            })
            .catch(err => {
                if (isMounted) {
                    console.error(err);
                    setError(err.userMessage || 'Failed to load analysis history');
                    setLoading(false);
                }
            });
        return () => { isMounted = false; };
    }, []);

    const openModal = async (record: HistoryRecord) => {
        setModal({ open: true, record, details: null, detailLoading: true });
        try {
            const details = await getFullResults(record.analysis_id);
            setModal(m => ({ ...m, details, detailLoading: false }));
        } catch {
            setModal(m => ({ ...m, detailLoading: false }));
        }
    };

    const closeModal = () => setModal({ open: false, record: null, details: null, detailLoading: false });

    /* ── helpers ── */
    const getRiskBadgeClass = (risk?: string) => {
        if (!risk) return 'hbadge-neutral';
        if (risk === 'HIGH' || risk === 'CRITICAL') return 'hbadge-red';
        if (risk === 'MEDIUM') return 'hbadge-yellow';
        return 'hbadge-green';
    };

    const getDecisionClass = (d?: string) => {
        if (!d) return '';
        if (d === 'APPROVE') return 'decision-approve';
        if (d === 'REJECT') return 'decision-reject';
        return 'decision-conditional';
    };

    const decisionLabel = (d?: string) =>
        d === 'APPROVE' ? '✓ Approved' : d === 'REJECT' ? '✗ Rejected' : d === 'CONDITIONAL' ? '~ Conditional' : '-';

    const fmtDate = (s: string) => {
        if (!s) return 'Unknown';
        try { return new Date(s).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
        catch { return 'Unknown'; }
    };

    const fmtAmount = (n?: number) => n ? `₹${(n / 100000).toFixed(1)} L` : '-';

    const getStatusBadge = (status: string, reason?: string) => {
        if (status === 'completed') return <span className="status-badge status-success"><CheckCircle size={12}/> Completed</span>;
        if (status === 'failed') return <span className="status-badge status-fail" title={reason}><X size={12}/> Failed</span>;
        return <span className="status-badge status-processing"><Loader size={12}/> Processing</span>;
    };

    /* ── filtered list ── */
    const filtered = history.filter(r => {
        if (search && !(r.company_name || '').toLowerCase().includes(search.toLowerCase())) return false;
        if (filterRisk !== 'ALL' && r.fraud_risk_level !== filterRisk) return false;
        if (filterDecision !== 'ALL' && r.decision !== filterDecision) return false;
        if (filterFraud === 'YES' && (!r.fraud_risk_level || r.fraud_risk_level === 'LOW')) return false;
        if (filterFraud === 'NO' && r.fraud_risk_level && r.fraud_risk_level !== 'LOW') return false;
        return true;
    });

    /* ─────────────────────────────────────────────────── */
    return (
        <div className="history-page">
            {!hideNavbar && (
                <nav className="history-navbar">
                    <Link to="/" className="logo-container">
                        <Zap size={24} fill="#0d3b38" stroke="none" />
                        <span>CreditIQ AI</span>
                    </Link>
                    <div className="nav-center-title"><Clock size={16} /> Analysis Portfolio History</div>
                    <Link to="/newanalysis" className="btn btn-primary btn-sm">Run New Analysis</Link>
                </nav>
            )}

            <div className="history-container">
                {/* Header */}
                <div className="history-header">
                    <div className="history-header-left">
                        <h1>Portfolio Audit Log</h1>
                        <p>All historically processed credit appraisals archived by the CreditIQ engine.</p>
                    </div>
                    <div className="history-header-stats">
                        <div className="hstat"><span className="hstat-val">{history.length}</span><span className="hstat-lbl">Total</span></div>
                        <div className="hstat"><span className="hstat-val" style={{color:'#10B981'}}>{history.filter(r=>r.decision==='APPROVE').length}</span><span className="hstat-lbl">Approved</span></div>
                        <div className="hstat"><span className="hstat-val" style={{color:'#DC2626'}}>{history.filter(r=>r.decision==='REJECT').length}</span><span className="hstat-lbl">Rejected</span></div>
                        <div className="hstat"><span className="hstat-val" style={{color:'#F59E0B'}}>{history.filter(r=>r.fraud_risk_level==='HIGH').length}</span><span className="hstat-lbl">High Fraud</span></div>
                    </div>
                </div>

                {/* Filters Bar */}
                <div className="hfilter-bar">
                    <div className="hfilter-search">
                        <Search size={16} />
                        <input placeholder="Search company name..." value={search} onChange={e => setSearch(e.target.value)} />
                        {search && <button onClick={() => setSearch('')}><X size={14}/></button>}
                    </div>
                    <div className="hfilter-selects">
                        <div className="hfilter-select-wrap">
                            <Filter size={14}/><select value={filterRisk} onChange={e => setFilterRisk(e.target.value)}>
                                <option value="ALL">All Risk</option>
                                <option value="HIGH">High Risk</option>
                                <option value="MEDIUM">Medium Risk</option>
                                <option value="LOW">Low Risk</option>
                            </select><ChevronDown size={14}/>
                        </div>
                        <div className="hfilter-select-wrap">
                            <select value={filterDecision} onChange={e => setFilterDecision(e.target.value)}>
                                <option value="ALL">All Decisions</option>
                                <option value="APPROVE">Approved</option>
                                <option value="REJECT">Rejected</option>
                                <option value="CONDITIONAL">Conditional</option>
                            </select><ChevronDown size={14}/>
                        </div>
                        <div className="hfilter-select-wrap">
                            <ShieldAlert size={14}/><select value={filterFraud} onChange={e => setFilterFraud(e.target.value)}>
                                <option value="ALL">All Fraud</option>
                                <option value="YES">Fraud Flagged</option>
                                <option value="NO">Clean</option>
                            </select><ChevronDown size={14}/>
                        </div>
                    </div>
                    {(filterRisk !== 'ALL' || filterDecision !== 'ALL' || filterFraud !== 'ALL' || search) && (
                        <button className="hfilter-clear" onClick={() => { setSearch(''); setFilterRisk('ALL'); setFilterDecision('ALL'); setFilterFraud('ALL'); }}>
                            <X size={14}/> Clear Filters
                        </button>
                    )}
                </div>

                {/* Content */}
                {loading ? (
                    <div className="history-loading">
                        <div className="h-spinner" />
                        <p>Fetching historical archives...</p>
                    </div>
                ) : error ? (
                    <div className="history-error">
                        <AlertTriangle size={40} color="#DC2626" />
                        <h3>{error}</h3>
                        <p>Ensure the backend is running on port 8000.</p>
                    </div>
                ) : history.length === 0 ? (
                    <div className="history-empty">
                        <FileText size={48} color="#CBD5E1" />
                        <h2>No analysis history available</h2>
                        <p>Run your first credit appraisal to populate this audit log.</p>
                        <Link to="/newanalysis" className="btn btn-primary" style={{ marginTop: '1.5rem', display: 'inline-flex', gap: '8px' }}>
                            Run First Analysis <ArrowRight size={16}/>
                        </Link>
                    </div>
                ) : (
                    <>
                        <div className="history-table-wrapper">
                            <table className="history-table">
                                <thead>
                                    <tr>
                                        <th><Building2 size={13}/> Company</th>
                                        <th><Calendar size={13}/> Date</th>
                                        <th>Loan Ask</th>
                                        <th>Decision</th>
                                        <th>Status</th>
                                        <th><TrendingUp size={13}/> PD %</th>
                                        <th><ShieldAlert size={13}/> Fraud</th>
                                        <th>CAM</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filtered.length === 0 ? (
                                        <tr><td colSpan={9} style={{ textAlign: 'center', padding: '3rem', color: '#94A3B8' }}>No records match current filters.</td></tr>
                                    ) : filtered.map(record => (
                                        <tr key={record.analysis_id} className={record.status === 'failed' ? 'row-failed' : ''}>
                                            <td>
                                                <div className="hcell-company">
                                                    <div className="hcompany-avatar">{record.company_name?.[0] ?? '?'}</div>
                                                    <div>
                                                        <div className="hcompany-name">{record.company_name}</div>
                                                        <div className="hcompany-sub">{record.gstin_number || record.cin_number || `#${record.analysis_id}`}</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="hcell-date">{fmtDate(record.created_at)}</td>
                                            <td className="hcell-amount">{fmtAmount(record.loan_amount_requested)}</td>
                                            <td>
                                                {record.status === 'completed' && record.decision ? (
                                                    <span className={`decision-pill ${getDecisionClass(record.decision)}`}>
                                                        {decisionLabel(record.decision)}
                                                    </span>
                                                ) : <span className="hcell-na">—</span>}
                                            </td>
                                            <td>{getStatusBadge(record.status, record.failure_reason)}</td>
                                            <td>
                                                {record.probability_of_default != null ? (
                                                    <div className="hpd-wrap">
                                                        <span className="hpd-val" style={{
                                                            color: record.probability_of_default > 40 ? '#DC2626' :
                                                                   record.probability_of_default > 20 ? '#D97706' : '#10B981'
                                                        }}>{record.probability_of_default.toFixed(1)}%</span>
                                                        <div className="hpd-bar">
                                                            <div className="hpd-fill" style={{
                                                                width: `${Math.min(record.probability_of_default, 100)}%`,
                                                                background: record.probability_of_default > 40 ? '#DC2626' :
                                                                            record.probability_of_default > 20 ? '#D97706' : '#10B981'
                                                            }} />
                                                        </div>
                                                    </div>
                                                ) : <span className="hcell-na">—</span>}
                                            </td>
                                            <td>
                                                <span className={`hbadge ${getRiskBadgeClass(record.fraud_risk_level)}`}>
                                                    {record.fraud_risk_level || '—'}
                                                </span>
                                            </td>
                                            <td>
                                                <span className={`hbadge ${record.cam_status === 'generated' ? 'hbadge-green' : 'hbadge-neutral'}`}>
                                                    {record.cam_status === 'generated' ? 'Ready' : 'Pending'}
                                                </span>
                                            </td>
                                            <td className="action-cell">
                                                {record.status === 'completed' ? (
                                                    <button className="btn-view" onClick={() => openModal(record)}>
                                                        Details <ArrowRight size={13}/>
                                                    </button>
                                                ) : (
                                                    <Link to={`/analysis?id=${record.analysis_id}`} className="btn-view btn-view-resume">
                                                        Resume <ArrowRight size={13}/>
                                                    </Link>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <div className="h-table-footer">
                            Showing {filtered.length} of {history.length} records
                        </div>
                    </>
                )}
            </div>

            {/* ── DETAIL MODAL ── */}
            {modal.open && modal.record && (
                <div className="hmodal-overlay" onClick={closeModal}>
                    <div className="hmodal" onClick={e => e.stopPropagation()}>
                        <div className="hmodal-header">
                            <div>
                                <div className="hmodal-title">{modal.record.company_name}</div>
                                <div className="hmodal-sub">Analysis #{modal.record.analysis_id} · {fmtDate(modal.record.created_at)}</div>
                            </div>
                            <button className="hmodal-close" onClick={closeModal}><X size={20}/></button>
                        </div>

                        {modal.detailLoading ? (
                            <div style={{ textAlign: 'center', padding: '3rem' }}>
                                <div className="h-spinner" style={{ margin: '0 auto 1rem' }} />
                                <p style={{ color: '#64748B' }}>Loading full analysis...</p>
                            </div>
                        ) : modal.details ? (
                            <div className="hmodal-body">

                                {/* Summary row */}
                                <div className="hmodal-summary-row">
                                    {[
                                        { label: 'Decision', value: decisionLabel(modal.details.decision?.decision), bold: true },
                                        { label: 'Probability of Default', value: `${modal.details.decision?.probability_of_default?.toFixed(1)}%` },
                                        { label: 'Recommended Loan', value: fmtAmount(modal.details.decision?.recommended_loan_amount) },
                                        { label: 'Interest Rate', value: `${modal.details.decision?.recommended_interest_rate?.toFixed(2)}%` },
                                        { label: 'Data Quality', value: `${modal.details.decision?.data_quality_score?.toFixed(0)}%` },
                                    ].map(({ label, value }) => (
                                        <div key={label} className="hmodal-summary-cell">
                                            <div className="hmodal-cell-label">{label}</div>
                                            <div className="hmodal-cell-val">{value}</div>
                                        </div>
                                    ))}
                                </div>

                                {/* Fraud insights */}
                                <div className="hmodal-section">
                                    <div className="hmodal-section-title"><ShieldAlert size={16}/> Fraud Insights</div>
                                    <div className="hmodal-fraud-row">
                                        <span className={`hbadge hbadge-lg ${getRiskBadgeClass(modal.details.fraud?.overall_fraud_risk)}`}>
                                            {modal.details.fraud?.overall_fraud_risk} Risk
                                        </span>
                                        <span style={{ color: '#64748B', fontSize: '0.875rem' }}>
                                            {modal.details.fraud?.total_signals_found} signal(s) detected
                                        </span>
                                    </div>
                                    {modal.details.fraud?.signals?.length > 0 && (
                                        <div className="hmodal-signals">
                                            {modal.details.fraud.signals.map((sig, i) => (
                                                <div key={i} className="hmodal-signal-row">
                                                    <span className={`hbadge ${getRiskBadgeClass(sig.risk_level)}`}>{sig.risk_level}</span>
                                                    <span className="hmodal-signal-type">{sig.type}</span>
                                                    <span className="hmodal-signal-desc">{sig.description}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                {/* SHAP factors */}
                                <div className="hmodal-section">
                                    <div className="hmodal-section-title"><Activity size={16}/> SHAP Risk Drivers</div>
                                    <div className="hmodal-shap">
                                        {modal.details.shap?.shap_factors?.slice(0, 6).map((f, i) => (
                                            <div key={i} className="hmodal-shap-row">
                                                <span className="hmodal-shap-name">{f.name}</span>
                                                <span className={`hmodal-shap-impact ${parseFloat(f.impact) > 0 ? 'shap-neg' : 'shap-pos'}`}>
                                                    {parseFloat(f.impact) > 0 ? '▲' : '▼'} {Math.abs(parseFloat(f.impact)).toFixed(3)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Decision reasoning */}
                                {modal.details.recommendation?.decision_reasoning && (
                                    <div className="hmodal-section">
                                        <div className="hmodal-section-title"><FileText size={16}/> Analyst Reasoning</div>
                                        <p className="hmodal-reasoning">{modal.details.recommendation.decision_reasoning}</p>
                                    </div>
                                )}

                                {/* Action buttons */}
                                <div className="hmodal-actions">
                                    <Link to={`/dashboard?id=${modal.record.analysis_id}`} className="btn btn-primary" style={{ gap: '8px', display: 'inline-flex' }}>
                                        Full Report <ArrowRight size={15}/>
                                    </Link>
                                    <button className="btn-view" onClick={closeModal}>Close</button>
                                </div>
                            </div>
                        ) : (
                            <div style={{ padding: '2rem', color: '#64748B', textAlign: 'center' }}>
                                Could not load detailed results. <Link to={`/dashboard?id=${modal.record.analysis_id}`}>Open Full Report →</Link>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default History;
