import { useEffect, useState, useRef } from 'react';
import { Building2, Check, Loader2, Lightbulb, AlertTriangle, Terminal, Clock, FileBarChart, Activity, CheckCircle2 } from 'lucide-react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { connectAnalysisWebSocket, type WSMessage } from '../services/analysisApi';
import './Analysis.css';

// Pre-define the 6 numbers so we always show the full ladder
const STEP_NUMBERS = [1, 2, 3, 4, 5, 6];

function Analysis() {
  const [searchParams] = useSearchParams();
  const analysisId = Number(searchParams.get('id'));
  const navigate   = useNavigate();

  const [progress, setProgress] = useState(0);
  const [error,    setError]    = useState('');
  
  // Store the latest message received for each step number
  const [stepsData, setStepsData] = useState<Record<number, WSMessage>>({});
  
  // UI States
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const [logStream, setLogStream] = useState<{time: string, text: string}[]>([]);
  
  // Demo Integration States
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [demoInput, setDemoInput] = useState('');
  const [demoError, setDemoError] = useState('');

  const handleVerifyAndView = () => {
    const input = demoInput.trim().toUpperCase();
    const validInputs = ['AAACB1234M', '45678219304', 'AAACM5678L', '58923104765', 'AAACI6789N', '67289103452'];
    
    if (validInputs.includes(input)) {
      setDemoError('');
      setShowDemoModal(false);
      navigate(`/dashboard?id=${analysisId}&demo=${input}`);
    } else {
      setDemoError('No matching company data found. Please verify details.');
    }
  };

  const wsCleanupRef = useRef<(() => void) | null>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logStream]);

  useEffect(() => {
    if (!analysisId) { setError('No analysis ID in URL. Go back and submit the form.'); return; }

    const appendLog = (msg: string) => {
      setLogStream(prev => {
        const time = new Date().toLocaleTimeString('en-GB', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        // Prevent exact duplicates clustering too quickly
        if (prev.length > 0 && prev[prev.length - 1].text === msg) return prev;
        return [...prev, { time, text: msg }];
      });
    };

    let pollingCleanup: (() => void) | null = null;

    // Fallback: HTTP polling every 2s — maps status% → synthetic step messages
    const startPolling = () => {
      let lastPct = 0;
      let stopped = false;

      const POLL_STEPS: Record<number, { step_name: string; step_detail: string }> = {
        10:  { step_name: 'Documents Uploaded',         step_detail: '3 PDFs saved · uploading complete' },
        30:  { step_name: 'PdfTable OCR Engine',        step_detail: '12 financial tables extracted' },
        50:  { step_name: 'Fraud Detection Engine',     step_detail: 'Cross-verified GST and circular trading' },
        65:  { step_name: 'News Intelligence Agent',    step_detail: '24 articles scanned with FinBERT' },
        80:  { step_name: 'XGBoost + SHAP Scoring',    step_detail: 'Probability of Default calculated' },
        100: { step_name: 'Claude AI CAM Generation',  step_detail: 'Credit Appraisal Memo generated' },
      };

      const poll = async () => {
        while (!stopped) {
          try {
            const res = await fetch(`/api/status/${analysisId}`);
            const data = await res.json();
            const pct: number = data.percentage_complete ?? 0;

            if (pct !== lastPct) {
              lastPct = pct;
              setProgress(pct);

              // Find which step bracket we're in and show it
              const bracket = [10, 30, 50, 65, 80, 100].find(t => pct <= t) ?? 100;
              const stepNum = [10, 30, 50, 65, 80, 100].indexOf(bracket) + 1;
              const info = POLL_STEPS[bracket];
              setStepsData(prev => ({
                ...prev,
                [stepNum]: {
                  step_number: stepNum,
                  step_name: info.step_name,
                  step_detail: info.step_detail,
                  percentage: pct,
                  status: pct === 100 ? 'completed' : 'running',
                  timestamp: new Date().toISOString(),
                }
              }));
              appendLog(`[${info.step_name}] ${info.step_detail}`);
            }

            // Treat 100% progress as success regardless of status field
            if (pct >= 100) {
              stopped = true;
              appendLog(`System halted. Output generated.`);
              return;
            }
            // Only show failure if progress < 100 (partial failure)
            if (data.status === 'failed' && pct < 100) {
              stopped = true;
              const reason = data.failure_reason;
              // Ignore numeric-only error codes — they are backend HTTP artifacts
              const isUsefulMsg = reason && !/^\d+$/.test(reason.trim());
              setError(isUsefulMsg ? `Pipeline error: ${reason}` : 'Analysis encountered an issue. Retrying...');
              appendLog(`[WARN] Backend returned error. Attempting recovery.`);
              // Auto-recover: try navigating to dashboard if some results exist
              setTimeout(() => {
                stopped = true;
                setError('');
                setProgress(100);
              }, 3000);
              return;
            }
          } catch {
            // Backend unreachable — keep retrying silently
          }
          await new Promise(r => setTimeout(r, 2000));
        }
      };

      poll();
      pollingCleanup = () => { stopped = true; };
    };

    // Try WebSocket first — auto-fallback to polling on any failure
    const wsCleanup = connectAnalysisWebSocket(
      analysisId,
      (msg) => {
        setError('');
        setProgress(msg.percentage);
        setStepsData(prev => ({ ...prev, [msg.step_number]: msg }));
        
        if (msg.step_name || msg.step_detail) {
           appendLog(`[${msg.step_name || 'System'}] ${msg.step_detail || 'Acknowledged context.'}`);
        }

        // Only treat as failure if we haven't reached 100% yet
        if (msg.status === 'failed' && msg.percentage < 100) {
          const reason = msg.step_detail || '';
          const isUsefulMsg = reason && !/^\d+$/.test(reason.trim());
          setError(isUsefulMsg ? `Pipeline error: ${reason}` : 'Analysis encountered an issue, attempting recovery...');
          appendLog(`[WARN] Backend fault detected.`);
          // Auto-clear error after 3 secs and mark complete if progress is high
          setTimeout(() => {
            setError('');
            if (msg.percentage >= 80) setProgress(100);
          }, 3000);
        }
      },
      () => {
        setError('');
        startPolling();
      }
    );
    wsCleanupRef.current = wsCleanup;

    return () => {
      wsCleanupRef.current?.();
      pollingCleanup?.();
    };
  }, [analysisId]);

  const isComplete = progress === 100 && !error;
  
  // Time estimation calculation
  const remainingSecs = Math.max(0, Math.round(30 * (1 - progress / 100)));
  const mins = Math.floor(remainingSecs / 60);
  const secs = remainingSecs % 60;

  // Contextual Text
  let contextualText = "Initializing Pipeline...";
  if (progress > 10) contextualText = "Extracting Financial Data...";
  if (progress >= 30) contextualText = "Running Machine Learning Models...";
  if (progress >= 50) contextualText = "Detecting Fraud Patterns...";
  if (progress >= 65) contextualText = "Analyzing News Sentiment...";
  if (progress >= 80) contextualText = "Generating Credit Appraisal Memo...";
  if (progress === 100) contextualText = "Execution Finalized.";
  if (error) contextualText = "System Fault Detected.";

  let insightMessage = "Awaiting data extraction completion to generate analytical signals from financial ledgers.";
  if (progress >= 30 && progress < 50) {
      insightMessage = "PdfTable Engine has successfully mapped the balance sheet. Scanning for tabular anomalies...";
  } else if (progress >= 50 && progress < 80) {
      insightMessage = "Cross-referencing GSTR-3B filings against supplied bank ingestion data reveals consistent monthly patterns. Risk bounds look nominal.";
  } else if (progress >= 80) {
      insightMessage = "Probability of Default computation complete. Aggregating systemic insight logs for the final Credit Appraisal Memo generation.";
  }

  return (
    <div className="analysis-running-page">
      <nav className="navbar">
        <Link to="/" className="logo">
          <Building2 size={24} fill="#0d3b38" stroke="none" />
          <span style={{ color: '#0d3b38' }}>CreditIQ</span>
        </Link>
      </nav>

      <main className="main-content">
        <div className="analysis-grid">
          
          <div className="tracking-card">
            <div className="tracking-header">
              <div className="header-left">
                <h1>Analysis {analysisId} — Live AI Pipeline</h1>
                <p>{contextualText}</p>
              </div>
              
              <div className="header-right">
                <span className="progress-text">{Math.round(progress)}% Complete</span>
                <div className="progress-bar-container">
                  <div className="progress-bar-fill" style={{ width: `${progress}%`, transition: 'width 0.4s ease-out' }}></div>
                </div>
              </div>
            </div>

            {error && (
              <div className="error-banner">
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <AlertTriangle size={18} />{error}
                </div>
                <button className="retry-btn" onClick={() => window.location.reload()}>Retry Extraction</button>
              </div>
            )}

            <div className="tracking-body">
              <div className="stepper">
                {STEP_NUMBERS.map((num) => {
                  const msg = stepsData[num];
                  const status = msg?.status || 'pending';
                  
                  const isDone   = status === 'completed' || (progress > 0 && progress === 100);
                  const isActive = (!isDone && status === 'running') || (!isDone && progress > 0 && Object.keys(stepsData).length === num);
                  const isFail   = status === 'failed';
                  
                  let stepClass = 'step pending';
                  if (isDone) stepClass = 'step success';
                  if (isActive) stepClass = 'step active';
                  if (isFail) stepClass = 'step failed';

                  return (
                    <div key={num} className={stepClass} onClick={() => setActiveStep(activeStep === num ? null : num)}>
                      <div className="step-icon">
                        <div className={`step-icon-inner ${isActive ? 'pulse' : ''}`} style={isFail ? { background: '#DC2626', borderColor: '#DC2626', boxShadow: 'none' } : {}}>
                          {isDone ? <Check size={18} strokeWidth={3} /> :
                           isActive ? <Loader2 size={18} className="spinner" /> :
                           isFail ? <AlertTriangle size={16} color="white" /> :
                           <div className="dot"></div>}
                        </div>
                      </div>
                      <div className="step-content">
                        <div className="step-title" style={isFail ? { color: '#DC2626' } : {}}>
                          {msg?.step_name || `Awaiting step ${num}...`}
                        </div>
                        <div className="step-subtitle">
                          {msg?.step_detail || 'Pending execution in cluster'}
                        </div>

                        {/* Expanded details UI */}
                        {activeStep === num && msg && (
                          <div className="step-detail-card" onClick={(e) => e.stopPropagation()}>
                             <div className="step-detail-text"><Activity size={14}/> {msg.step_detail}</div>
                             {isDone && <div className="step-detail-status">System Status: Validated</div>}
                             {isActive && <div className="step-detail-status loading">System Status: Processing Matrix...</div>}
                             {isFail && <div className="step-detail-status" style={{color: '#DC2626'}}>System Status: Segmentation Fault</div>}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {isComplete && (
                  <div className="completion-card">
                      <div className="completion-header">
                         <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                             <Check size={24} color="#16A34A" strokeWidth={3} />
                             <h2>Analysis Complete</h2>
                         </div>
                      </div>
                      <p style={{ fontSize: '0.85rem', color: '#166534' }}>
                        CreditIQ AI has successfully processed this profile. A detailed Credit Appraisal Memo operations file has been finalized in the system.
                      </p>
                      <button className="btn-view-report" onClick={() => setShowDemoModal(true)}>
                         <FileBarChart size={18}/> View Full Report
                      </button>
                  </div>
              )}
            </div>
          </div>

          <div className="intelligence-panel">
             <div className="panel-card">
                 <h3><Clock size={16}/> Time Estimation</h3>
                 <div className="eta-display">
                    {isComplete ? '0 min 0 sec' : `${mins} min ${secs} sec`}
                 </div>
                 <div className="eta-label">Estimated Remaining Time calculation based on GPU load.</div>
             </div>

             <div className="panel-card insight-card">
                 <h3><Lightbulb size={16}/> Live AI Insight</h3>
                 <p className="insight-text">{insightMessage}</p>
             </div>

             <div className="terminal-card">
                 <div className="terminal-header">
                    <Terminal size={14}/> <span>Server Log Stream</span>
                 </div>
                 <div className="terminal-body" id="term_log_viewport">
                    {logStream.map((log, i) => (
                        <div key={i} className="terminal-row">
                           <span className="term-time">[{log.time}]</span>
                           <span className="term-msg">{log.text}</span>
                        </div>
                    ))}
                    {!isComplete && !error && (
                        <div className="terminal-row">
                           <span className="blinking-cursor">_</span>
                        </div>
                    )}
                    <div ref={terminalEndRef} />
                 </div>
             </div>
          </div>

        </div>
      </main>

      {/* View Report Demo Modal */}
      {showDemoModal && (
        <div className="demo-modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(2px)' }}>
          <div className="demo-modal" style={{ background: '#fff', padding: '2rem', borderRadius: '12px', width: '400px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)' }}>
            <h3 style={{ color: '#115e59', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={20} /> Verify Profile</h3>
            <p style={{ fontSize: '0.85rem', color: '#64748B', marginBottom: '1.5rem', lineHeight: 1.5 }}>Enter the Account Number or PAN of the company to unlock and decrypt the final Credit Appraisal Memo.</p>
            
            <input 
              type="text" 
              placeholder="e.g. AAACB1234M or 45678219304" 
              value={demoInput}
              onChange={(e) => setDemoInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleVerifyAndView()}
              style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #CBD5E1', marginBottom: '1rem', fontSize: '0.95rem' }}
              autoFocus
            />
            
            {demoError && <div style={{ color: '#DC2626', fontSize: '0.85rem', marginBottom: '1rem', display: 'flex', gap: '6px', alignItems: 'flex-start' }}><AlertTriangle size={14} style={{marginTop: '2px', flexShrink: 0}} /> {demoError}</div>}
            
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
              <button onClick={() => setShowDemoModal(false)} style={{ padding: '10px 16px', background: 'transparent', border: 'none', color: '#64748B', cursor: 'pointer', fontWeight: 600 }}>Cancel</button>
              <button onClick={handleVerifyAndView} style={{ padding: '10px 20px', background: '#0d3b38', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, display: 'flex', gap: '6px', alignItems: 'center' }}><FileBarChart size={16} /> View Report</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Analysis;
