import { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  CheckCircle, Bell, AlertTriangle, Smartphone,
  TrendingUp, ShieldCheck, Activity, WifiOff, RefreshCw,
} from 'lucide-react';
import { acknowledgeAlert } from '../services/ewsApi';
import './WarningSystem.css';

/* ── helpers ──────────────────────────────────────────── */
function scoreColor(s: number) {
  if (s > 80) return '#EF4444';
  if (s >= 60) return '#F97316';
  if (s >= 30) return '#F59E0B';
  return '#10B981';
}
function riskColor(level: string) {
  const u = (level || '').toUpperCase();
  if (u === 'CRITICAL' || u === 'HIGH') return '#EF4444';
  if (u === 'MEDIUM') return '#F59E0B';
  return '#10B981';
}

/* Animated number – counts from `from` to `to` in 700ms */
function AnimNum({ value, decimals = 1 }: { value: number; decimals?: number }) {
  const [display, setDisplay] = useState(value);
  const raf = useRef<number>(0);
  const prev = useRef(value);

  useEffect(() => {
    const from = prev.current;
    const to = value;
    const duration = 700;
    const start = performance.now();
    const animate = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out-cubic
      setDisplay(from + (to - from) * eased);
      if (t < 1) raf.current = requestAnimationFrame(animate);
      else prev.current = to;
    };
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf.current);
  }, [value]);

  return <>{display.toFixed(decimals)}</>;
}

/* Countdown ring to next WebSocket update */
function Countdown({ seconds = 30 }: { seconds?: number }) {
  const [left, setLeft] = useState(seconds);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setLeft(seconds);
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      setLeft(prev => {
        if (prev <= 1) { clearInterval(intervalRef.current!); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [seconds]);

  const pct = (left / seconds) * 100;
  const r = 14, circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: '#64748B', fontWeight: 600 }}>
      <svg width={36} height={36} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={18} cy={18} r={r} fill="none" stroke="#E2E8F0" strokeWidth={3} />
        <circle cx={18} cy={18} r={r} fill="none" stroke="#14b8a6" strokeWidth={3}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" style={{ transition: 'stroke-dasharray 1s linear' }} />
        <text x={18} y={22} textAnchor="middle" style={{ fill: '#334155', fontSize: 9, fontWeight: 700, transform: 'rotate(90deg)', transformOrigin: '18px 18px' }}>
          {left}s
        </text>
      </svg>
      Next update
    </div>
  );
}

/* ── Main Component ────────────────────────────────────── */
function WarningSystem() {
  const [searchParams] = useSearchParams();
  const companyId = Number(searchParams.get('company_id') || '1');
  const analysisId = searchParams.get('id') || '1';

  const [data, setData] = useState<any>(null);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'live' | 'disconnected'>('connecting');
  const [lastUpdated, setLastUpdated] = useState('');
  const [updateCount, setUpdateCount] = useState(0);  // increments each WS message → triggers countdown reset
  const [flashedSignals, setFlashedSignals] = useState<Set<string>>(new Set());
  const [flashPage, setFlashPage] = useState(false); // brief page-wide glow on new data
  const [ackLoading, setAckLoading] = useState<number | null>(null);

  const prevSignals = useRef<Record<string, number>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const reconnTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const WS_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');

  const connect = useCallback(() => {
    if (reconnTimer.current) clearTimeout(reconnTimer.current);
    setWsStatus('connecting');
    const ws = new WebSocket(`${WS_BASE}/ws/ews/${companyId}`);
    wsRef.current = ws;

    ws.onopen = () => setWsStatus('live');

    ws.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        if (payload.type === 'error') return;

        /* Detect changed signals → flash those cards */
        const newFlashed = new Set<string>();
        for (const sig of (payload.signals || [])) {
          const prev = prevSignals.current[sig.signal_name];
          if (prev !== undefined && prev !== sig.score) newFlashed.add(sig.signal_name);
          prevSignals.current[sig.signal_name] = sig.score;
        }
        if (newFlashed.size > 0) {
          setFlashedSignals(newFlashed);
          setTimeout(() => setFlashedSignals(new Set()), 2500);
        }

        /* Page-wide green pulse on every update */
        setFlashPage(true);
        setTimeout(() => setFlashPage(false), 800);

        setData(payload);
        setLastUpdated(new Date().toLocaleTimeString());
        setUpdateCount(c => c + 1);
      } catch {/* ignore parse errors */ }
    };

    ws.onclose = () => {
      setWsStatus('disconnected');
      reconnTimer.current = setTimeout(connect, 5000);
    };
    ws.onerror = () => ws.close();
  }, [companyId, WS_BASE]);

  useEffect(() => {
    connect();
    return () => { wsRef.current?.close(); if (reconnTimer.current) clearTimeout(reconnTimer.current); };
  }, [connect]);

  const handleAck = async (alertId: number) => {
    setAckLoading(alertId);
    try { await acknowledgeAlert(alertId); }
    catch (e: any) { alert(e.userMessage || 'Could not acknowledge.'); }
    finally { setAckLoading(null); }
  };

  /* ── Loading ──────────────────────────────────────────── */
  if (!data) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '80vh', gap: 20 }}>
      <div style={{ width: 52, height: 52, border: '4px solid #E2E8F0', borderTopColor: '#14b8a6', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
      <div style={{ fontWeight: 700, color: '#475569', fontSize: '1.1rem' }}>Connecting to EWS Live Feed…</div>
      <div style={{ fontSize: '0.82rem', color: '#94A3B8' }}>ws://localhost:8000/ws/ews/{companyId}</div>
    </div>
  );

  const { company_info: ci, trajectory: traj, signals, alerts_sent, summary } = data;
  const CHART_PX = 200;
  const maxPd = Math.max(...traj.data_points.map((d: any) => d.probability_of_default), (traj.alert_threshold || 25) + 6);

  return (
    <div className="warning-page" style={{
      outline: flashPage ? '3px solid rgba(20,184,166,0.4)' : '3px solid transparent',
      outlineOffset: '-3px',
      transition: 'outline 0.3s ease',
    }}>

      {/* ── Navbar ─────────────────────────────────────── */}
      <nav className="warning-navbar">
        <Link to="/" className="warning-logo">
          <div style={{ background: '#0F172A', color: 'white', padding: 6, borderRadius: 8, display: 'flex' }}>
            <ShieldCheck size={22} strokeWidth={2.5} />
          </div>
          CreditIQ
        </Link>

        <div className="warning-nav-right">
          {/* WS Status Badge */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '7px 14px', borderRadius: 20,
            background: wsStatus === 'live' ? '#ECFDF5' : wsStatus === 'connecting' ? '#FFF7ED' : '#FEF2F2',
            color: wsStatus === 'live' ? '#065F46' : wsStatus === 'connecting' ? '#92400E' : '#991B1B',
            fontWeight: 800, fontSize: '0.78rem', letterSpacing: '0.04em',
          }}>
            {wsStatus === 'live'
              ? <><div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981', animation: 'pulse-green 1.5s infinite' }} /> LIVE</>
              : wsStatus === 'connecting'
                ? <><RefreshCw size={12} style={{ animation: 'spin 1s linear infinite' }} /> CONNECTING</>
                : <><WifiOff size={12} /> RECONNECTING</>
            }
          </div>

          {/* Countdown */}
          {wsStatus === 'live' && <Countdown key={updateCount} seconds={30} />}

          {lastUpdated && (
            <div style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 600 }}>
              Last sync: <strong style={{ color: '#1E293B' }}>{lastUpdated}</strong>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, borderLeft: '1px solid #E2E8F0', paddingLeft: 20 }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.82rem', fontWeight: 800, color: '#0F172A' }}>RM Dashboard</div>
              <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#64748B' }}>{ci.relationship_manager_name}</div>
            </div>
            <div style={{ width: 38, height: 38, borderRadius: '50%', background: 'linear-gradient(135deg,#1E293B,#334155)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 800, fontSize: '0.85rem' }}>RM</div>
          </div>
        </div>
      </nav>

      {/* ── Body ───────────────────────────────────────── */}
      <div className="warning-container">

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '2.5rem' }}>
          <div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 800, letterSpacing: '-0.04em', margin: 0 }}>Early Warning System</h1>
            <div className="warning-subtitle">
              <strong>{ci.company_name}</strong> · Real-Time WebSocket · Exposure: ₹{(ci.loan_amount_disbursed / 10_000_000).toFixed(1)} Cr
              <span style={{ marginLeft: 14, opacity: 0.6 }}>· Since {ci.disbursement_date}</span>
            </div>
          </div>
          <div style={{
            background: 'linear-gradient(135deg,#14b8a6,#0891b2)',
            borderRadius: 16, padding: '12px 20px', textAlign: 'center',
            boxShadow: '0 8px 24px rgba(20,184,166,0.3)',
          }}>
            <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'rgba(255,255,255,0.7)', letterSpacing: '0.06em' }}>EWS SCORE</div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: 'white', lineHeight: 1.1 }}>
              <AnimNum value={summary.overall_ews_score} /><span style={{ fontSize: '1rem', opacity: 0.7 }}>/100</span>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)', fontWeight: 600, marginTop: 2 }}>
              {summary.risk_trend}
            </div>
          </div>
        </div>

        {/* ── PD Trajectory Chart ───────────────────────── */}
        <div className="trajectory-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontWeight: 800, fontSize: '1.2rem', color: '#1E293B' }}>
                <TrendingUp size={22} color="#0d9488" />
                90-Day Probability of Default (PD) Projection
              </div>
              <div style={{ color: traj.alert_triggered ? '#EF4444' : '#10B981', fontSize: '0.9rem', marginTop: 5, fontWeight: 600 }}>
                {traj.alert_triggered
                  ? '⚠ Critical Breach — Trajectory exceeds risk threshold.'
                  : '✓ Steady — Probability within acceptable range.'}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Current PD</div>
              <div style={{ color: traj.current_pd >= traj.alert_threshold ? '#EF4444' : '#10B981', fontSize: '2.4rem', fontWeight: 800, letterSpacing: '-0.05em', lineHeight: 1 }}>
                <AnimNum value={traj.current_pd} />%
              </div>
            </div>
          </div>

          {/* Bars */}
          <div className="trajectory-chart">
            {/* Threshold line */}
            <div style={{
              position: 'absolute', left: 0, right: 0,
              bottom: Math.round((traj.alert_threshold / maxPd) * CHART_PX),
              height: 2, borderBottom: '2px dashed #EF4444',
              zIndex: 1, opacity: 0.55, pointerEvents: 'none',
            }}>
              <div style={{ position: 'absolute', right: 4, top: -20, fontSize: '0.65rem', color: '#EF4444', fontWeight: 800, background: '#FEF2F2', padding: '2px 6px', borderRadius: 4 }}>
                THRESHOLD {traj.alert_threshold}%
              </div>
            </div>

            {traj.data_points.map((pt: any, i: number) => {
              const barPx = Math.max(6, Math.round((pt.probability_of_default / maxPd) * CHART_PX));
              const isAlert = traj.alert_triggered && pt.month === traj.alert_trigger_month;
              const barCol = pt.probability_of_default >= traj.alert_threshold ? '#EF4444'
                : pt.is_predicted ? '#94A3B8' : '#10B981';
              return (
                <div key={i} className="trajectory-bar-col">
                  <div className="trajectory-bar-wrapper">
                    <div
                      className={`trajectory-bar ${pt.is_predicted ? 'bar-predicted' : ''}`}
                      style={{
                        height: barPx,
                        backgroundColor: barCol,
                        boxShadow: pt.probability_of_default >= traj.alert_threshold
                          ? '0 0 18px rgba(239,68,68,0.45)'
                          : '0 4px 10px rgba(16,185,129,0.25)',
                        animationDelay: `${i * 80}ms`,
                      }}
                    >
                      {isAlert && <div className="alert-label">⚠</div>}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.76rem', fontWeight: 800, color: '#334155', marginTop: 8 }}>
                    {pt.month}{pt.is_predicted ? ' (E)' : ''}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: barCol, fontWeight: 800 }}>
                    {pt.probability_of_default}%
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Alerts ────────────────────────────────────── */}
        {alerts_sent.length > 0 && (
          <div className="alerts-section">
            <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0F172A', display: 'flex', alignItems: 'center', gap: 10 }}>
              <Activity size={22} color="#EA580C" />
              Active Telemetry &amp; SMS Alerts
              <span style={{ background: '#FEF2F2', color: '#991B1B', fontSize: '0.7rem', fontWeight: 800, padding: '3px 10px', borderRadius: 20 }}>
                {alerts_sent.filter((a: any) => !a.acknowledged).length} Active
              </span>
            </h2>
            {alerts_sent.map((alert: any) => (
              <div key={alert.alert_id} className={`alert-card ${alert.acknowledged ? 'alert-acknowledged' : 'alert-active'}`}>
                <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
                  <div style={{ background: alert.acknowledged ? '#ECFDF5' : '#FEF2F2', color: riskColor(alert.severity), padding: 12, borderRadius: 14 }}>
                    {alert.acknowledged ? <CheckCircle size={22} /> : <AlertTriangle size={22} />}
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 800, color: riskColor(alert.severity), fontSize: '0.68rem', letterSpacing: '0.05em' }}>
                        {String(alert.severity).toUpperCase()} PRIORITY
                      </span>
                      <span style={{ fontSize: '0.72rem', color: '#94A3B8' }}>
                        · {new Date(alert.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#1E293B', marginTop: 4 }}>{alert.message}</div>
                    <div style={{ fontSize: '0.82rem', color: '#64748B', marginTop: 5, display: 'flex', gap: 14 }}>
                      <span>System: {alert.source}</span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Smartphone size={13} color="#0891b2" /> {alert.channels_used?.join(' & ')}
                      </span>
                    </div>
                  </div>
                </div>
                {alert.acknowledged
                  ? <div style={{ color: '#10B981', background: '#ECFDF5', padding: '7px 14px', borderRadius: 10, fontSize: '0.82rem', fontWeight: 800 }}>Resolved ✓</div>
                  : <button onClick={() => handleAck(alert.alert_id)} disabled={ackLoading === alert.alert_id}
                    style={{ background: '#0F172A', color: 'white', border: 'none', padding: '10px 18px', borderRadius: 12, cursor: 'pointer', fontSize: '0.86rem', fontWeight: 700 }}>
                    {ackLoading === alert.alert_id ? 'Syncing…' : 'Acknowledge'}
                  </button>
                }
              </div>
            ))}
          </div>
        )}

        {/* ── Live Signal Grid ───────────────────────────── */}
        <div style={{ marginTop: '3.5rem' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0F172A', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: 10 }}>
            <Activity size={22} color="#14b8a6" />
            Live Signal Monitor
            <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#94A3B8' }}>
              · Auto-updates every 30s via WebSocket · {updateCount} refreshes
            </span>
          </h2>
          <div className="signals-grid">
            {signals.map((sig: any, i: number) => {
              const col = scoreColor(sig.score || 0);
              const isFlash = flashedSignals.has(sig.signal_name);
              const isLive = (sig.source || '').includes('[LIVE]');
              return (
                <div key={i} className="signal-card" style={{
                  borderTop: `5px solid ${col}`,
                  boxShadow: isFlash
                    ? `0 0 0 3px ${col}60, 0 8px 24px rgba(0,0,0,0.08)`
                    : '0 4px 12px rgba(0,0,0,0.04)',
                  transform: isFlash ? 'scale(1.02)' : 'scale(1)',
                  transition: 'all 0.4s cubic-bezier(0.34,1.56,0.64,1)',
                }}>
                  {/* Live badge */}
                  {isLive && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6 }}>
                      <span style={{ background: '#ECFDF5', color: '#065F46', fontSize: '0.6rem', fontWeight: 800, padding: '2px 7px', borderRadius: 10, letterSpacing: '0.04em' }}>
                        ● LIVE
                      </span>
                    </div>
                  )}
                  <div className="signal-card-name">{String(sig.signal_name).replace(/_/g, ' ')}</div>
                  <div className="signal-score" style={{ color: col }}>
                    <AnimNum value={sig.score || 0} decimals={0} />
                    <span style={{ fontSize: '1rem', color: '#CBD5E1', marginLeft: 4 }}>/100</span>
                  </div>
                  {/* Mini bar */}
                  <div style={{ height: 6, borderRadius: 3, background: '#F1F5F9', margin: '10px 0', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', borderRadius: 3, background: col,
                      width: `${Math.min(100, sig.score || 0)}%`,
                      transition: 'width 0.8s ease',
                    }} />
                  </div>
                  <div className="signal-detail">{sig.detail}</div>
                  <div style={{ marginTop: 'auto', paddingTop: 14 }}>
                    <div style={{ fontSize: '0.62rem', color: '#94A3B8', fontWeight: 800, textTransform: 'uppercase' }}>Source</div>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#475569' }}>{sig.source}</div>
                    {sig.last_updated && (
                      <div style={{ fontSize: '0.62rem', color: '#CBD5E1', marginTop: 3 }}>
                        {new Date(sig.last_updated).toLocaleTimeString()}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Recommendation Banner ─────────────────────── */}
        <div className="summary-banner" style={{
          background: traj.alert_triggered
            ? 'linear-gradient(135deg,#FEF2F2,#FEE2E2)'
            : 'linear-gradient(135deg,#ECFDF5,#D1FAE5)',
          border: `1px solid ${traj.alert_triggered ? '#FCA5A5' : '#6EE7B7'}`,
          marginTop: '3rem',
        }}>
          <div style={{ background: traj.alert_triggered ? '#EF4444' : '#10B981', color: 'white', padding: 14, borderRadius: 14, flexShrink: 0 }}>
            <Bell size={26} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.1rem', color: traj.alert_triggered ? '#991B1B' : '#065F46' }}>
              Recommended Risk Escalation Protocol
            </div>
            <div style={{ marginTop: 6, fontSize: '0.95rem', fontWeight: 500, lineHeight: 1.6, color: traj.alert_triggered ? '#B91C1C' : '#047857' }}>
              {summary.recommended_action}
            </div>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginTop: '3.5rem' }}>
          <Link to={`/dashboard?id=${analysisId}`} style={{
            background: '#F8FAFC', color: '#1E293B', border: '1px solid #E2E8F0',
            fontWeight: 700, padding: '12px 30px', borderRadius: 14,
            textDecoration: 'none', display: 'inline-block',
          }}>
            ← Return to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}

export default WarningSystem;
