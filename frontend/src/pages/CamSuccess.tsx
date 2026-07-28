import { useState, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  FileText, Loader2, Download, CheckCircle, Plus, Bell,
  ClipboardList, MapPin, Building2, Users, Eye, ChevronRight,
  AlertTriangle, ShieldCheck, Banknote,
} from 'lucide-react';
import { getCAMPreview, generateCAM, downloadCAM } from '../services/camApi';
import { useApi, Skeleton, ErrorBanner } from '../services/useApi';
import './CamSuccess.css';

/* ── Observation fields the analyst must fill before generating ──────── */
const OBS_FIELDS = [
  {
    id: 'factory_visit',
    icon: Building2,
    label: 'Factory / Office Visit',
    placeholder: 'e.g. Visited the factory at MIDC Pune. Observed 3 production lines, ~85% operational capacity. Clean premises, inventory levels adequate. All machinery appeared regularly maintained.',
    required: true,
  },
  {
    id: 'promoter_meeting',
    icon: Users,
    label: 'Promoter / Director Meeting',
    placeholder: 'e.g. Met with Mr. Rajesh Sharma (MD) and Mrs. Priya Sharma (Director). Confident, articulate, 18 years experience in sector. No red flags observed during interaction.',
    required: true,
  },
  {
    id: 'market_reference',
    icon: MapPin,
    label: 'Market / Industry Reference Check',
    placeholder: 'e.g. Spoke with 2 competitors and 3 suppliers in local market. Company has good reputation for timely payments. One competitor confirmed order wins from the same clients.',
    required: true,
  },
  {
    id: 'collateral_inspection',
    icon: Eye,
    label: 'Collateral / Asset Inspection',
    placeholder: 'e.g. Inspected land parcel at Survey No. 45, Taluka Haveli. Boundaries match title deed. Current market value estimated ₹3.2 Cr by Sub-registrar reference rates.',
    required: false,
  },
  {
    id: 'banker_feedback',
    icon: Banknote,
    label: 'Banker / Creditor Feedback',
    placeholder: 'e.g. Account conduct with Bank of Maharashtra: satisfactory for 4 years. CC limit of ₹1.5 Cr utilized at ~70%. No cheque bounces in last 12 months per statement reviewed.',
    required: false,
  },
  {
    id: 'additional_remarks',
    icon: ClipboardList,
    label: 'Additional Analyst Remarks',
    placeholder: 'e.g. Concern: GST payment slightly delayed in Q2 FY24. Promoter explained cash flow mismatch due to delayed customer payment by State Govt. Acceptable. Overall positive impression.',
    required: false,
  },
];

/* ── Step indicator ──────────────────────────────────────────────────── */
function Steps({ current }: { current: number }) {
  const steps = ['Analyst Input', 'Generate CAM', 'Download Report'];
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: '2.5rem' }}>
      {steps.map((label, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', flex: i < steps.length - 1 ? 1 : 'none' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 36, height: 36, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: i < current ? '#10B981' : i === current ? '#0d3b38' : '#E2E8F0',
              color: i <= current ? 'white' : '#94A3B8',
              fontWeight: 800, fontSize: '0.82rem', transition: 'all 0.3s',
            }}>
              {i < current ? <CheckCircle size={16} /> : i + 1}
            </div>
            <div style={{ fontSize: '0.68rem', fontWeight: 700, color: i === current ? '#0d3b38' : '#94A3B8', whiteSpace: 'nowrap' }}>{label}</div>
          </div>
          {i < steps.length - 1 && (
            <div style={{ flex: 1, height: 2, background: i < current ? '#10B981' : '#E2E8F0', margin: '0 8px', marginBottom: 22, transition: 'background 0.3s' }} />
          )}
        </div>
      ))}
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────────────────── */
function CamSuccess() {
  const [searchParams] = useSearchParams();
  const analysisId = Number(searchParams.get('id') || '1');

  const { data: preview, loading, error, refetch } = useApi(() => getCAMPreview(analysisId), [analysisId]);

  /* Step state: 0 = form, 1 = generating, 2 = done */
  const [step, setStep] = useState(0);
  const [observations, setObservations] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState('');
  const [camMeta, setCamMeta] = useState<any>(null);
  const [, setGenerating] = useState(false);
  const [genError, setGenError] = useState('');
  const [genProgress, setGenProgress] = useState(0);
  const [genDetail, setGenDetail] = useState('');
  const [showToast, setShowToast] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  /* Validate required fields */
  const validate = () => {
    for (const f of OBS_FIELDS.filter(f => f.required)) {
      if (!observations[f.id]?.trim()) {
        setFormError(`"${f.label}" is a required field. Please complete it before generating the CAM.`);
        return false;
      }
    }
    setFormError('');
    return true;
  };

  /* Build observations string for backend */
  const buildObsText = () =>
    OBS_FIELDS
      .filter(f => observations[f.id]?.trim())
      .map(f => `${f.label}:\n${observations[f.id].trim()}`)
      .join('\n\n');

  /* Handle form submit → generate */
  const handleProceed = async () => {
    if (!validate()) return;
    setStep(1);
    setGenerating(true);
    setGenError('');
    setGenProgress(5);
    setGenDetail('Connecting to Cohere AI engine...');

    /* WS progress */
    const ws = new WebSocket(`ws://localhost:8000/ws/analysis/${analysisId}`);
    wsRef.current = ws;
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.status === 'running' || d.status === 'completed') {
          setGenProgress(d.percentage);
          setGenDetail(d.step_detail || '');
        }
      } catch { }
    };

    try {
      const result = await generateCAM(analysisId, buildObsText());
      setCamMeta(result);
      setGenProgress(100);
      setGenDetail('Document synthesis complete.');
      setStep(2);
    } catch (e: any) {
      setGenError(e.userMessage || 'CAM generation failed. Please retry.');
      setStep(0);
    } finally {
      setGenerating(false);
      ws.close();
    }
  };

  const handleDownload = (format: 'word' | 'pdf') => {
    downloadCAM(analysisId, format);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  if (loading) return (
    <div style={{ padding: '2rem' }}>
      <Skeleton height={50} style={{ marginBottom: 16 }} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 24 }}>
        <div><Skeleton height={100} style={{ marginBottom: 12 }} /><Skeleton height={200} /></div>
        <Skeleton height={320} />
      </div>
    </div>
  );

  return (
    <div className="cam-page" style={{ position: 'relative' }}>

      {/* Toast */}
      {showToast && (
        <div style={{ position: 'fixed', top: 24, right: 24, zIndex: 9999, background: '#16A34A', color: 'white', padding: '14px 28px', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 10, boxShadow: '0 20px 40px rgba(0,0,0,0.15)', fontWeight: 700, fontSize: '0.95rem' }}>
          <CheckCircle size={20} /> Document downloaded successfully!
        </div>
      )}

      {/* Navbar */}
      <nav className="cam-navbar">
        <Link to="/" className="cam-logo">
          <div style={{ background: '#0d3b38', color: 'white', padding: '6px 8px', borderRadius: 8, marginRight: 8 }}>
            <FileText size={18} strokeWidth={2.5} />
          </div>
          CreditIQ · CAM Engine
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748B', background: '#F1F5F9', padding: '6px 12px', borderRadius: 8 }}>
            Analysis ID: #{analysisId}
          </div>
          <Link to={`/dashboard?id=${analysisId}`} style={{ color: '#0d3b38', fontSize: '0.88rem', textDecoration: 'none', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
            ← Back to Dashboard
          </Link>
        </div>
      </nav>

      <div className="cam-container">
        <ErrorBanner message={error || genError} onRetry={error ? refetch : () => setStep(0)} />

        {/* Decision Banner */}
        {preview && (
          <div style={{
            background: preview.decision === 'APPROVE' ? 'linear-gradient(135deg,#ECFDF5,#D1FAE5)' : preview.decision === 'REJECT' ? 'linear-gradient(135deg,#FEF2F2,#FEE2E2)' : 'linear-gradient(135deg,#FFFBEB,#FEF3C7)',
            border: `1px solid ${preview.decision === 'APPROVE' ? '#6EE7B7' : preview.decision === 'REJECT' ? '#FCA5A5' : '#FCD34D'}`,
            borderRadius: 16, padding: '20px 28px', marginBottom: '2.5rem',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{ fontSize: '0.7rem', fontWeight: 800, letterSpacing: '0.08em', color: '#64748B', textTransform: 'uppercase', marginBottom: 4 }}>AI Credit Decision</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 900, letterSpacing: '-0.04em', color: preview.decision === 'APPROVE' ? '#065F46' : preview.decision === 'REJECT' ? '#991B1B' : '#92400E' }}>
                {preview.decision}
              </div>
              <div style={{ fontSize: '0.85rem', color: '#64748B', marginTop: 4, maxWidth: 480, lineHeight: 1.5 }}>
                {preview.executive_summary?.slice(0, 120)}...
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end' }}>
              {preview.key_findings.slice(0, 2).map((f: string, i: number) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(255,255,255,0.7)', padding: '6px 12px', borderRadius: 8, fontSize: '0.78rem', fontWeight: 600, color: '#334155' }}>
                  <CheckCircle size={13} color="#10B981" /> {f}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step Progress */}
        <Steps current={step} />

        {/* ── STEP 0: Analyst Field Observation Form ─────────────────────── */}
        {step === 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '2rem' }}>
            <div>
              <div style={{ background: 'white', borderRadius: 20, border: '1px solid #E2E8F0', overflow: 'hidden', boxShadow: '0 4px 24px rgba(0,0,0,0.05)' }}>
                {/* Form Header */}
                <div style={{ background: 'linear-gradient(135deg,#0d3b38,#14564f)', padding: '24px 32px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{ background: 'rgba(255,255,255,0.15)', padding: 12, borderRadius: 12 }}>
                      <ClipboardList size={26} color="white" />
                    </div>
                    <div>
                      <div style={{ color: 'white', fontWeight: 800, fontSize: '1.25rem', letterSpacing: '-0.02em' }}>Field Observation Report</div>
                      <div style={{ color: 'rgba(255,255,255,0.65)', fontSize: '0.82rem', marginTop: 3 }}>
                        Document what you observed during the site visit. This will be embedded directly into the CAM.
                      </div>
                    </div>
                  </div>
                </div>

                {/* Fields */}
                <div style={{ padding: '28px 32px' }}>
                  {OBS_FIELDS.map((field) => {
                    const Icon = field.icon;
                    return (
                      <div key={field.id} style={{ marginBottom: 28 }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, fontWeight: 700, fontSize: '0.88rem', color: '#1E293B' }}>
                          <div style={{ background: '#F1F5F9', padding: 6, borderRadius: 8 }}>
                            <Icon size={15} color="#0d3b38" />
                          </div>
                          {field.label}
                          {field.required && <span style={{ color: '#EF4444', fontSize: '0.7rem', fontWeight: 800 }}>REQUIRED</span>}
                          {!field.required && <span style={{ color: '#94A3B8', fontSize: '0.7rem', fontWeight: 600 }}>optional</span>}
                        </label>
                        <textarea
                          id={`obs-${field.id}`}
                          value={observations[field.id] || ''}
                          onChange={(e) => setObservations(prev => ({ ...prev, [field.id]: e.target.value }))}
                          placeholder={field.placeholder}
                          rows={3}
                          style={{
                            width: '100%', padding: '12px 14px', border: `1.5px solid ${observations[field.id]?.trim() ? '#14b8a6' : '#E2E8F0'}`,
                            borderRadius: 10, fontSize: '0.88rem', fontFamily: 'inherit', lineHeight: 1.6, color: '#334155',
                            background: '#FAFAFA', resize: 'vertical', outline: 'none', transition: 'border-color 0.2s',
                            boxSizing: 'border-box',
                          }}
                          onFocus={e => e.target.style.borderColor = '#14b8a6'}
                          onBlur={e => e.target.style.borderColor = observations[field.id]?.trim() ? '#14b8a6' : '#E2E8F0'}
                        />
                      </div>
                    );
                  })}

                  {formError && (
                    <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 10, padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'center', marginBottom: 20, color: '#991B1B', fontSize: '0.88rem', fontWeight: 600 }}>
                      <AlertTriangle size={16} /> {formError}
                    </div>
                  )}

                  <button
                    onClick={handleProceed}
                    style={{
                      width: '100%', padding: '16px', background: 'linear-gradient(135deg,#0d3b38,#0d9488)',
                      color: 'white', border: 'none', borderRadius: 12, cursor: 'pointer',
                      fontWeight: 800, fontSize: '1rem', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10,
                      boxShadow: '0 8px 24px rgba(13,148,136,0.35)', transition: 'transform 0.2s',
                      letterSpacing: '-0.01em',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.transform = 'translateY(-2px)')}
                    onMouseLeave={e => (e.currentTarget.style.transform = 'translateY(0)')}
                  >
                    <ShieldCheck size={20} />
                    Generate Credit Appraisal Memorandum
                    <ChevronRight size={18} />
                  </button>
                </div>
              </div>
            </div>

            {/* Right side info */}
            <div>
              <div style={{ background: 'white', borderRadius: 16, border: '1px solid #E2E8F0', padding: '24px', marginBottom: 16, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
                <div style={{ fontWeight: 800, color: '#1E293B', marginBottom: 16, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FileText size={16} color="#14b8a6" /> What this CAM includes
                </div>
                {[
                  'Verification Detail Table',
                  'Guarantor & Director Analysis',
                  'Reference Checks (Market, Banker, Creditor)',
                  'Compliance & Legal Status',
                  'CAT Sheet & Financial Ratios',
                  'Group Analysis (DSCR, TOL/TNW)',
                  'Visit Report from your observations',
                  'AI-computed Conditions for Approval',
                  'Credit Score & Risk Summary',
                ].map((item, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 10, color: '#475569', fontSize: '0.82rem', alignItems: 'flex-start' }}>
                    <CheckCircle size={14} color="#10B981" style={{ marginTop: 1, flexShrink: 0 }} />
                    {item}
                  </div>
                ))}
              </div>

              {preview && (
                <div style={{ background: 'linear-gradient(135deg,#F8FAFC,#F1F5F9)', borderRadius: 16, border: '1px solid #E2E8F0', padding: '20px' }}>
                  <div style={{ fontWeight: 800, color: '#1E293B', marginBottom: 12, fontSize: '0.88rem' }}>AI Integrity Assessment</div>
                  <div style={{ fontSize: '0.82rem', color: '#64748B', lineHeight: 1.6 }}>{preview.fraud_summary}</div>
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #E2E8F0', fontSize: '0.82rem', color: '#64748B', lineHeight: 1.6 }}>{preview.credit_score_summary}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── STEP 1: Generating ─────────────────────────────────────────── */}
        {step === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 420, gap: 32 }}>
            <div style={{ position: 'relative', width: 100, height: 100 }}>
              <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: '6px solid #E2E8F0' }} />
              <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: '6px solid transparent', borderTopColor: '#0d3b38', borderRightColor: '#14b8a6', animation: 'spin 1s linear infinite' }} />
              <div style={{ position: 'absolute', inset: 16, borderRadius: '50%', background: 'linear-gradient(135deg,#0d3b38,#0d9488)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <FileText size={24} color="white" />
              </div>
            </div>

            <div style={{ textAlign: 'center', maxWidth: 500 }}>
              <div style={{ fontWeight: 800, fontSize: '1.5rem', color: '#1E293B', letterSpacing: '-0.03em', marginBottom: 8 }}>
                Generating Credit Appraisal Memorandum
              </div>
              <div style={{ fontSize: '0.95rem', color: '#64748B', lineHeight: 1.6 }}>
                Cohere AI is synthesizing your document with analyst observations and real credit data. This takes ~60-90 seconds.
              </div>
            </div>

            <div style={{ width: '100%', maxWidth: 500 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.82rem', fontWeight: 700, color: '#475569' }}>
                <span>{genDetail || 'Processing...'}</span>
                <span style={{ color: '#0d3b38' }}>{genProgress}%</span>
              </div>
              <div style={{ height: 10, background: '#E2E8F0', borderRadius: 5, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${genProgress}%`, background: 'linear-gradient(90deg,#0d3b38,#14b8a6)', borderRadius: 5, transition: 'width 0.5s ease', boxShadow: '0 0 8px rgba(20,184,166,0.4)' }} />
              </div>
            </div>

            {/* Steps being performed */}
            {[
              { label: 'RAG context compiled from analysis data', done: genProgress > 10 },
              { label: 'Analyst field observations embedded', done: genProgress > 25 },
              { label: 'Cohere document synthesis in progress', done: genProgress > 50 },
              { label: 'Tables & sections being structured', done: genProgress > 75 },
              { label: 'Word document finalized', done: genProgress > 90 },
            ].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.82rem', color: s.done ? '#10B981' : '#94A3B8', fontWeight: s.done ? 700 : 500, transition: 'color 0.3s' }}>
                {s.done ? <CheckCircle size={15} /> : <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />}
                {s.label}
              </div>
            ))}
          </div>
        )}

        {/* ── STEP 2: Done — Download ────────────────────────────────────── */}
        {step === 2 && camMeta && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '2rem' }}>

            {/* Left: Preview */}
            <div style={{ background: 'white', borderRadius: 20, border: '1px solid #E2E8F0', overflow: 'hidden', boxShadow: '0 4px 24px rgba(0,0,0,0.06)' }}>
              <div style={{ background: 'linear-gradient(135deg,#064E3B,#065F46)', padding: '24px 32px', display: 'flex', alignItems: 'center', gap: 14 }}>
                <div style={{ background: 'rgba(255,255,255,0.15)', padding: 12, borderRadius: 12 }}>
                  <CheckCircle size={26} color="white" />
                </div>
                <div>
                  <div style={{ color: 'white', fontWeight: 800, fontSize: '1.2rem' }}>CAM Generated Successfully</div>
                  <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.8rem', marginTop: 3 }}>
                    Generated in {camMeta.generation_time_minutes?.toFixed(1)} mins · {camMeta.pages_count} sections · Ready for download
                  </div>
                </div>
              </div>

              <div style={{ padding: '28px 32px' }}>
                <div style={{ fontWeight: 800, color: '#1E293B', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FileText size={16} color="#0891b2" /> Executive Summary (AI-Generated)
                </div>
                <p style={{ color: '#475569', lineHeight: 1.7, fontSize: '0.92rem', background: '#F8FAFC', padding: '16px 20px', borderRadius: 12, border: '1px solid #E2E8F0' }}>
                  "{preview?.executive_summary}"
                </p>

                <div style={{ marginTop: 24 }}>
                  <div style={{ fontWeight: 800, color: '#1E293B', marginBottom: 14 }}>Key Credit Findings</div>
                  {preview?.key_findings.map((f: string, i: number) => (
                    <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 12, alignItems: 'flex-start', padding: '10px 14px', background: '#F8FAFC', borderRadius: 10, border: '1px solid #F1F5F9' }}>
                      <CheckCircle size={16} color="#10B981" style={{ flexShrink: 0, marginTop: 1 }} />
                      <span style={{ fontSize: '0.88rem', color: '#334155', lineHeight: 1.5 }}>{f}</span>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: 20, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div style={{ background: '#FEF2F2', borderRadius: 12, padding: '16px', border: '1px solid #FECACA' }}>
                    <div style={{ fontWeight: 800, color: '#B91C1C', marginBottom: 8, fontSize: '0.82rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Integrity Profile</div>
                    <p style={{ color: '#7F1D1D', fontSize: '0.82rem', lineHeight: 1.5 }}>{preview?.fraud_summary}</p>
                  </div>
                  <div style={{ background: '#F0FDF4', borderRadius: 12, padding: '16px', border: '1px solid #BBF7D0' }}>
                    <div style={{ fontWeight: 800, color: '#15803D', marginBottom: 8, fontSize: '0.82rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Credit Scoring</div>
                    <p style={{ color: '#166534', fontSize: '0.82rem', lineHeight: 1.5 }}>{preview?.credit_score_summary}</p>
                  </div>
                </div>

                {/* Observations included */}
                <div style={{ marginTop: 20, background: '#f0fdfa', borderRadius: 12, padding: '16px', border: '1px solid #99f6e4' }}>
                  <div style={{ fontWeight: 800, color: '#0f766e', marginBottom: 8, fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <ClipboardList size={14} /> Field Observations Embedded
                  </div>
                  <p style={{ color: '#0f766e', fontSize: '0.8rem', lineHeight: 1.5 }}>
                    Your analyst observations have been embedded verbatim into Section 8 (Visit Report) of this CAM.
                  </p>
                </div>
              </div>
            </div>

            {/* Right: Download */}
            <div>
              <div style={{ background: 'white', borderRadius: 16, border: '1px solid #E2E8F0', padding: '24px', boxShadow: '0 4px 16px rgba(0,0,0,0.04)', marginBottom: 16 }}>
                <div style={{ fontWeight: 800, fontSize: '1rem', color: '#1E293B', marginBottom: 20, textAlign: 'center' }}>
                  Download Official Document
                </div>

                <button onClick={() => handleDownload('word')} style={{
                  width: '100%', padding: '16px', background: 'linear-gradient(135deg,#0f766e,#0d9488)',
                  color: 'white', border: 'none', borderRadius: 12, cursor: 'pointer', fontWeight: 700,
                  marginBottom: 12, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10,
                  fontSize: '0.92rem', boxShadow: '0 4px 12px rgba(13,148,136,0.3)', transition: 'transform 0.2s',
                }}
                  onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-1px)'}
                  onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
                >
                  <Download size={18} /> Download as Word (.docx)
                </button>

                <button onClick={() => handleDownload('pdf')} style={{
                  width: '100%', padding: '16px', background: 'linear-gradient(135deg,#B91C1C,#DC2626)',
                  color: 'white', border: 'none', borderRadius: 12, cursor: 'pointer', fontWeight: 700,
                  display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10,
                  fontSize: '0.92rem', boxShadow: '0 4px 12px rgba(220,38,38,0.3)', transition: 'transform 0.2s',
                }}
                  onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-1px)'}
                  onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
                >
                  <FileText size={18} /> Download as PDF
                </button>

                <div style={{ marginTop: 16, padding: '12px 14px', background: '#F8FAFC', borderRadius: 10, border: '1px solid #E2E8F0', fontSize: '0.72rem', color: '#64748B', lineHeight: 1.6 }}>
                  This document is <strong>CONFIDENTIAL</strong> and generated by CreditIQ AI Credit Intelligence Platform.
                  For internal credit committee use only.
                </div>
              </div>

              {/* Sections */}
              {camMeta.sections_included && (
                <div style={{ background: 'white', borderRadius: 16, border: '1px solid #E2E8F0', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.03)', marginBottom: 16 }}>
                  <div style={{ fontWeight: 800, color: '#1E293B', marginBottom: 14, fontSize: '0.88rem' }}>Document Sections</div>
                  {camMeta.sections_included.map((s: string, i: number) => (
                    <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, fontSize: '0.8rem', color: '#64748B', alignItems: 'center' }}>
                      <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#14b8a6', flexShrink: 0 }} /> {s}
                    </div>
                  ))}
                </div>
              )}

              {/* Next actions */}
              <div style={{ background: 'white', borderRadius: 16, border: '1px dashed #CBD5E1', padding: '20px' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748B', fontWeight: 700, marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Next Actions</div>
                <Link to={`/warning-system?company_id=1&id=${analysisId}`} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', background: '#FFFBEB', border: '1px solid #FCD34D', borderRadius: 10, textDecoration: 'none', color: '#92400E', fontWeight: 600, marginBottom: 10, fontSize: '0.84rem' }}>
                  <div style={{ background: '#FEF3C7', padding: 6, borderRadius: 8 }}><Bell size={14} color="#EA580C" /></div> Monitor via EWS
                </Link>
                <Link to="/new-analysis" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', background: '#f0fdfa', border: '1px solid #99f6e4', borderRadius: 10, textDecoration: 'none', color: '#134e4a', fontWeight: 600, fontSize: '0.84rem' }}>
                  <div style={{ background: '#ccfbf1', padding: 6, borderRadius: 8 }}><Plus size={14} color="#0891b2" /></div> New Analysis
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default CamSuccess;
