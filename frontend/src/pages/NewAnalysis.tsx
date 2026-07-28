import { useState, useEffect } from 'react';
import { Triangle, CloudUpload, FileUp, FileText, TrendingUp, AlertOctagon, UserCheck, Newspaper, Briefcase, Quote, RefreshCw, CheckCircle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { uploadCompanyDocuments } from '../services/uploadApi';
import { triggerAnalysis } from '../services/analysisApi';
import { ErrorBanner } from '../services/useApi';
import { useAuth } from '../context/AuthContext';
import api from '../services/apiConfig';
import './NewAnalysis.css';

function NewAnalysis({ hideNavbar = false }: { hideNavbar?: boolean }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [formData, setFormData] = useState({ companyName: '', cin: '', gstin: '', pan: '', amount: '' });
  const [files, setFiles] = useState({ balanceSheet: null as File | null, bankStatements: null as File | null, gstFilings: null as File | null });
  const [uploadPct, setUploadPct] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  // Persistence States
  const [isFetching, setIsFetching] = useState(true);
  const [lastFilledTime, setLastFilledTime] = useState<string | null>(null);
  const [isAutofilled, setIsAutofilled] = useState(false);
  const [draftData, setDraftData] = useState<any>(null);

  useEffect(() => {
    const fetchLatest = async () => {
      try {
        const res = await api.get('/api/analysis/latest', {
          headers: { 'X-User-Email': user?.email || 'admin@gmail.com' }
        });
        if (res.data?.data) {
           const d = res.data.data;
           setDraftData(d);
           setFormData({
             companyName: d.company_name || '',
             cin: d.cin || '',
             gstin: d.gstin || '',
             pan: d.pan || '',
             amount: d.amount ? String(d.amount) : '',
           });
           setLastFilledTime(new Date(d.updated_at || d.created_at || new Date()).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }));
           setIsAutofilled(true);
        }
      } catch (e) {
        console.error("Failed to fetch draft", e);
      } finally {
        setIsFetching(false);
      }
    };
    
    // Short artificial delay to demonstrate the elegant loading state
    setTimeout(fetchLatest, 600);
  }, [user]);

  const handleLoadPrevious = () => {
      if (draftData) {
           setFormData({
             companyName: draftData.company_name || '',
             cin: draftData.cin || '',
             gstin: draftData.gstin || '',
             pan: draftData.pan || '',
             amount: draftData.amount ? String(draftData.amount) : '',
           });
           setIsAutofilled(true);
      }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setIsAutofilled(false);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, type: keyof typeof files) => {
    if (e.target.files?.[0]) setFiles({ ...files, [type]: e.target.files[0] });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    if (!formData.companyName || !formData.cin || !formData.gstin || !formData.pan || !formData.amount) {
      setErrorMsg('Please fill in all required text fields.'); return;
    }
    if (!files.balanceSheet || !files.bankStatements || !files.gstFilings) {
      setErrorMsg('Please upload all 3 required financial documents.'); return;
    }

    setIsSubmitting(true);
    setUploadPct(0);
    
    // Save data to Drafts (fire-and-forget)
    api.post('/api/analysis/save', {
      company_name: formData.companyName,
      cin_number: formData.cin,
      gstin_number: formData.gstin,
      pan_number: formData.pan,
      loan_amount: parseFloat(formData.amount) || 0
    }, {
      headers: { 'X-User-Email': user?.email || 'admin@gmail.com' }
    }).catch(console.error);

    try {
      // STEP 1: Upload files with real byte progress
      const result = await uploadCompanyDocuments({
        company_name:  formData.companyName,
        cin_number:    formData.cin,
        gstin_number:  formData.gstin,
        pan_number:    formData.pan,
        loan_amount:   formData.amount,
        balance_sheet: files.balanceSheet,
        bank_statement: files.bankStatements,
        gst_filing:    files.gstFilings,
        onProgress:    setUploadPct,
      });

      // STEP 2: Trigger analysis (fire-and-forget, backend processes async)
      triggerAnalysis(result.analysis_id).catch(console.error);

      // STEP 3: Go to the analysis loading screen
      navigate(`/analysis?id=${result.analysis_id}`);
    } catch (err: any) {
      setErrorMsg(err.userMessage || err.message || 'Upload failed. Check backend connection.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="analysis-page">
      {!hideNavbar && (
      <nav className="navbar">
        <div className="logo" style={{ color: '#0d3b38' }}>
          <Triangle size={24} fill="#0d3b38" stroke="none" style={{ transform: 'rotate(180deg)' }} />
          CreditIQ
        </div>
        <div className="nav-links">
          <Link to="/" className="nav-link">Home</Link>
          <span className="nav-separator">/</span>
          <Link to="/new-analysis" className="nav-link active" style={{ color: '#0d3b38' }}>New Analysis</Link>
        </div>
      </nav>
      )}

      <div className="layout-container">
        <div className="card form-card">
          <h1>New Credit Analysis</h1>
          <p className="subtitle">Enter company details and upload financial documents to begin</p>
          <div className="divider"></div>

          {isFetching && (
              <div className="fetch-banner">
                  <RefreshCw size={14} className="spin" /> Fetching previous analysis...
              </div>
          )}

          {lastFilledTime && !isFetching && (
              <div className="autofill-banner">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                     <CheckCircle size={14} /> Auto-filled from last entry on {lastFilledTime}
                  </div>
                  <button type="button" onClick={handleLoadPrevious} className="btn-load-prev">Load Previous Data</button>
              </div>
          )}

          <ErrorBanner message={errorMsg} onRetry={() => setErrorMsg('')} />

          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              {[
                { label: 'Company Name', name: 'companyName', placeholder: 'Enter legal entity name', value: formData.companyName },
                { label: 'CIN Number', name: 'cin', placeholder: '21-character CIN e.g. U28990MH2018PTC123456', value: formData.cin },
                { label: 'GSTIN Number', name: 'gstin', placeholder: '15-character GSTIN e.g. 27AAAPZ1234F1Z5', value: formData.gstin },
                { label: 'PAN Number', name: 'pan', placeholder: '10-character PAN e.g. AAAPZ1234F', value: formData.pan },
              ].map(({ label, name, placeholder, value }) => (
                <div className="form-group" key={name}>
                  <label className="form-label">{label} <span style={{ color: 'red' }}>*</span></label>
                  <input type="text" name={name} className={`form-input ${isAutofilled ? 'autofilled-glow' : ''}`} placeholder={placeholder}
                    value={value} onChange={handleInputChange} required />
                </div>
              ))}

              <div className="form-group full-width">
                <label className="form-label">Loan Amount Requested <span style={{ color: 'red' }}>*</span></label>
                <div className={`input-with-prefix ${isAutofilled ? 'autofilled-glow' : ''}`} style={{ border: isAutofilled ? '1.5px solid #0d9488' : '1px solid #e2e8f0', borderRadius: '0.375rem', overflow: 'hidden' }}>
                  <span className="input-prefix">₹</span>
                  <input type="number" name="amount" className="form-input" placeholder="e.g. 30000000 for ₹3 Crore"
                    style={{ border: 'none', borderRadius: 0, boxShadow: 'none' }}
                    value={formData.amount} onChange={handleInputChange} required />
                </div>
              </div>
            </div>

            <div style={{ marginTop: '2.5rem' }}>
              <h2>Upload Financial Documents <span style={{ color: 'red', fontSize: '1rem' }}>*</span></h2>
              <p className="subtitle" style={{ fontSize: '0.8rem', marginBottom: '1rem' }}>PDF format only. Max 10MB per file. All 3 required.</p>

              <div className="upload-grid">
                {([
                  { key: 'balanceSheet', label: 'Balance Sheet', sub: 'last 12 months', Icon: CloudUpload },
                  { key: 'bankStatements', label: 'Bank Statements', sub: 'Last 12 months', Icon: FileUp },
                  { key: 'gstFilings', label: 'GST Filings', sub: 'Last 12 months', Icon: FileText },
                ] as const).map(({ key, label, sub, Icon }) => {
                  const uploaded = !!files[key];
                  return (
                    <label key={key} className={`upload-card ${uploaded ? 'uploaded' : ''}`}
                      style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                      <input type="file" accept=".pdf" style={{ display: 'none' }}
                        onChange={(e) => handleFileChange(e, key)} />
                      <div className="upload-icon">
                        <Icon size={24} color={uploaded ? '#16a34a' : '#0d3b38'} />
                      </div>
                      <div className="upload-title" style={{ color: '#0d3b38' }}>{label}</div>
                      <div className="upload-subtitle">{sub}</div>
                      <div className="upload-link" style={{ color: uploaded ? '#16a34a' : '#0d3b38', fontWeight: uploaded ? 'bold' : 'normal', marginTop: 'auto' }}>
                        {uploaded ? `✅ ${files[key]!.name}` : 'Click to upload PDF'}
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Submit button with REAL upload progress */}
            <button type="submit" disabled={isSubmitting}
              style={{
                backgroundColor: isSubmitting ? '#0d3b38' : '#0d3b38',
                display: 'flex', border: 'none', width: '100%',
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                position: 'relative', overflow: 'hidden',
                borderRadius: 8, padding: '14px 24px', color: 'white',
                fontWeight: 700, fontSize: '1rem', justifyContent: 'center', gap: 8,
                marginTop: '2rem',
              }}>
              {/* Real upload progress fill */}
              {isSubmitting && (
                <div style={{
                  position: 'absolute', left: 0, top: 0, bottom: 0,
                  width: `${uploadPct}%`, background: 'rgba(255,255,255,0.15)',
                  transition: 'width 0.3s ease',
                }} />
              )}
              <span style={{ position: 'relative', zIndex: 1 }}>
                {isSubmitting
                  ? uploadPct < 100 ? `⬆️ Uploading... ${uploadPct}%` : '⚙️ Initialising CreditIQ Analysis...'
                  : '🚀 Run CreditIQ Analysis'}
              </span>
            </button>
            <p className="security-note" style={{ textAlign: 'center', marginTop: '1rem' }}>
              Your documents are processed securely. RBI-compliant audit trail maintained.
            </p>
          </form>
        </div>

        <div className="card sidebar-card enhanced-sidebar">
          <div className="sidebar-title">WHAT CreditIQ ANALYSES:</div>
          <div className="enhanced-features-list">
            {[
              {
                title: 'Financial ratios and trends', desc: 'Analyzes revenue, profitability, and growth', icon: <TrendingUp size={18} />, color: '#0d9488', bg: '#f0fdfa',
                data: [
                  { label: 'Revenue Growth', value: '12.5% YoY', highlight: true },
                  { label: 'Net Profit Margin', value: '8.2%', highlight: false },
                  { label: 'Debt-to-Equity', value: '1.4', highlight: false },
                  { label: 'Operating Cash Flow', value: '₹2.3 Cr', highlight: false },
                  { label: 'Trend', value: 'Stable growth', highlight: true, color: 'green' }
                ]
              },
              {
                title: 'GST mismatch and fraud', desc: 'Detects anomalies and fraudulent transactions', icon: <AlertOctagon size={18} />, color: '#DC2626', bg: '#FEF2F2',
                data: [
                  { label: 'Reported Sales', value: '₹5.8 Cr', highlight: false },
                  { label: 'Bank Transactions', value: '₹6.5 Cr', highlight: false },
                  { label: 'Mismatch', value: '₹0.7 Cr', highlight: true },
                  { label: 'Suspicious Trans.', value: '14', highlight: true, color: 'red' },
                  { label: 'Fraud Risk Level', value: 'Medium', highlight: true, color: 'yellow' }
                ]
              },
              {
                title: 'Promoter check', desc: 'Evaluates credibility and past records', icon: <UserCheck size={18} />, color: '#059669', bg: '#ECFDF5',
                data: [
                  { label: 'Name', value: 'Rahul Sharma', highlight: false },
                  { label: 'Experience', value: '12+ years', highlight: false },
                  { label: 'Prev. Companies', value: '3', highlight: false },
                  { label: 'Legal Cases', value: 'None', highlight: true, color: 'green' },
                  { label: 'Credibility Score', value: '82/100', highlight: true, color: 'green' }
                ]
              },
              {
                title: 'News and signals', desc: 'Uses AI to analyze sentiment from news', icon: <Newspaper size={18} />, color: '#D97706', bg: '#FFFBEB',
                data: [
                  { label: 'Sentiment', value: 'Neutral/Positive', highlight: false },
                  { label: 'Ext. Risk Score', value: '0.28', highlight: true, color: 'green' },
                  { label: 'News Alerts', value: '• Expanding ops\n• YoY growth', highlight: false }
                ]
              },
              {
                title: 'Sector risk scoring', desc: 'Applies industry-based risk models', icon: <Briefcase size={18} />, color: '#0891b2', bg: '#f0fdfa',
                data: [
                  { label: 'Industry', value: 'Textile Mfg', highlight: false },
                  { label: 'Sector Risk', value: 'Medium', highlight: true, color: 'yellow' },
                  { label: 'Demand Trend', value: 'Increasing', highlight: true, color: 'green' },
                  { label: 'Risk Score', value: '65/100', highlight: true, color: 'yellow' }
                ]
              }
            ].map((feat, i) => (
              <div key={i} className="enhanced-feature-card" style={{ animationDelay: `${i * 0.1}s`, display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '10px' }}>
                  <div className="enhanced-feature-icon" style={{ backgroundColor: feat.bg, color: feat.color }}>
                    {feat.icon}
                  </div>
                  <div className="enhanced-feature-text">
                    <div className="enhanced-feature-title">{feat.title}</div>
                    <div className="enhanced-feature-desc">{feat.desc}</div>
                  </div>
                </div>
                <div style={{ paddingLeft: '6px', borderLeft: '2px solid rgba(0,0,0,0.06)', marginLeft: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {feat.data.map((item, idx) => {
                     let valColor = '#334155';
                     if (item.color === 'green') valColor = '#059669';
                     if (item.color === 'yellow') valColor = '#D97706';
                     if (item.color === 'red') valColor = '#DC2626';

                     return (
                       <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', alignItems: 'flex-start', gap: '4px' }}>
                          <span style={{ color: '#64748B', whiteSpace: 'nowrap' }}>{item.label}:</span>
                          <span style={{ 
                              color: valColor, 
                              fontWeight: item.highlight ? 700 : 500,
                              textAlign: 'right',
                              whiteSpace: 'pre-line',
                              lineHeight: 1.2
                          }}>
                              {item.value}
                          </span>
                       </div>
                     );
                  })}
                </div>
              </div>
            ))}
          </div>

          <div className="enhanced-testimonial">
            <Quote size={32} className="quote-icon-bg" />
            <p className="enhanced-testimonial-text">
              "CreditIQ simplified our due diligence from weeks to minutes. A true game changer."
            </p>
            <div className="enhanced-testimonial-author">
              <div className="enhanced-author-avatar">FB</div>
              <div className="enhanced-author-info">
                <span className="enhanced-author-name">CTO</span>
                <span className="enhanced-author-company">FinBank India</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {!hideNavbar && (
        <footer className="footer">© 2024 CreditIQ AI Technologies. All rights reserved.</footer>
      )}
    </div>
  );
}

export default NewAnalysis;
