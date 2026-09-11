import React, { useState } from 'react';
import {
    LayoutDashboard, Users, Shield, History, LogOut, Search,
    FileText, AlertTriangle, BarChart3, RefreshCw,
    CheckCircle, Cpu, Activity, Lock, Globe, Clock,
    TrendingUp, Zap, Bell, ChevronDown, User,
    Save, Building, Briefcase, Key, ShieldCheck, Monitor
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import './AdminDashboard.css';
import HistoryPage from './History';
import NewAnalysis from './NewAnalysis';
import Chatbot from '../components/Chatbot';

// New Modular Components
import Sidebar from '../components/Dashboard/Sidebar';
import DashboardCard from '../components/Dashboard/DashboardCard';
import ChartSection from '../components/Dashboard/ChartSection';

/* ─── Profile Settings ────────────────────────────────────────── */
const ProfileSettings = ({ user }: { user: any }) => {
    const [name, setName] = useState(user?.name || '');
    const [org, setOrg] = useState('Vivriti Financial');
    const [dept, setDept] = useState('Risk & Compliance');
    const [emailNotif, setEmailNotif] = useState(true);
    const [fraudAlerts, setFraudAlerts] = useState(true);
    const [saved, setSaved] = useState(false);

    const handleSave = (e: React.FormEvent) => {
        e.preventDefault();
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
    };

    return (
        <motion.div 
            className="tab-content"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
        >
            <h2 className="tab-title">Profile Settings</h2>
            <form onSubmit={handleSave}>
                <div className="settings-layout">
                    {/* Left Column */}
                    <div className="settings-section" style={{ flex: 2 }}>
                        <h3 className="section-label">Personal Information</h3>
                        <div className="profile-edit-header" style={{ display: 'flex', alignItems: 'center', gap: '2rem', marginBottom: '2rem' }}>
                            <div className="profile-avatar" style={{ width: 80, height: 80, fontSize: '2rem' }}>{user?.name?.[0]?.toUpperCase() || 'A'}</div>
                            <button type="button" className="sidebar-logout" style={{ background: 'rgba(13, 148, 136, 0.1)', color: '#0d9488', border: '1px solid rgba(13, 148, 136, 0.2)', width: 'auto' }}>Change Avatar</button>
                        </div>
                        <div className="form-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                            <div className="form-group">
                                <label className="kl-label" style={{ marginBottom: 8, display: 'block' }}>Full Name</label>
                                <input type="text" className="form-input" value={name} onChange={e => setName(e.target.value)} required style={{ width: '100%' }} />
                            </div>
                            <div className="form-group">
                                <label className="kl-label" style={{ marginBottom: 8, display: 'block' }}>Email Address (Read-only)</label>
                                <input type="email" className="form-input disabled" value={user?.email || 'admin@creditiq.ai'} readOnly style={{ width: '100%', background: '#f1f5f9', color: '#94a3b8' }} />
                            </div>
                            <div className="form-group">
                                <label className="kl-label" style={{ marginBottom: 8, display: 'block' }}>Phone Number</label>
                                <input type="text" className="form-input" placeholder="+91 98765 43210" style={{ width: '100%' }} />
                            </div>
                            <div className="form-group">
                                <label className="kl-label" style={{ marginBottom: 8, display: 'block' }}>Role</label>
                                <input type="text" className="form-input disabled" value={user?.role?.toUpperCase() || 'SUPER ADMIN'} readOnly style={{ width: '100%', background: '#f1f5f9', color: '#94a3b8' }} />
                            </div>
                        </div>
                    </div>

                    {/* Right Column */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div className="settings-section">
                            <h3 className="section-label">Professional Info</h3>
                            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                                <label className="kl-label" style={{ marginBottom: 8, display: 'block' }}><Building size={14} style={{marginRight: 6, verticalAlign: 'text-bottom'}}/> Organization</label>
                                <input type="text" className="form-input" value={org} onChange={e => setOrg(e.target.value)} style={{ width: '100%' }} />
                            </div>
                            <div className="form-group">
                                <label className="kl-label" style={{ marginBottom: 8, display: 'block' }}><Briefcase size={14} style={{marginRight: 6, verticalAlign: 'text-bottom'}}/> Department</label>
                                <input type="text" className="form-input" value={dept} onChange={e => setDept(e.target.value)} style={{ width: '100%' }} />
                            </div>
                        </div>

                        <div className="settings-section">
                            <h3 className="section-label">Preferences</h3>
                            <div className="setting-toggle-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 0', borderBottom: '1px solid #f1f5f9' }}>
                                <span style={{ fontWeight: 500, fontSize: '0.9rem' }}>Email Notifications</span>
                                <div className={`toggle-switch ${emailNotif ? 'active' : ''}`} onClick={() => setEmailNotif(!emailNotif)}>
                                    <div className="toggle-knob" />
                                </div>
                            </div>
                            <div className="setting-toggle-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 0' }}>
                                <span style={{ fontWeight: 500, fontSize: '0.9rem' }}>Fraud Alerts (Instant)</span>
                                <div className={`toggle-switch ${fraudAlerts ? 'active' : ''}`} onClick={() => setFraudAlerts(!fraudAlerts)}>
                                    <div className="toggle-knob" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="settings-actions" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <motion.button 
                        type="submit" 
                        className="ap-retrain-btn" 
                        style={{ width: 'auto', padding: '0.85rem 2rem', marginTop: '2rem' }}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                    >
                        <Save size={16} /> Save Changes
                    </motion.button>
                    {saved && <span className="save-success-msg" style={{ marginTop: '2rem', color: '#10b981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle size={16}/> Profile updated successfully</span>}
                </div>
            </form>
        </motion.div>
    );
};

/* ─── Security Settings ───────────────────────────────────────── */
const SecuritySettings = () => {
    const { logout } = useAuth();
    const [mfa, setMfa] = useState(true);
    const [ipRestrict, setIpRestrict] = useState(false);
    const [sessionTimeout, setSessionTimeout] = useState('30m');
    const [saved, setSaved] = useState(false);
    const [showKey, setShowKey] = useState(false);
    
    const handlePassChange = (e: React.FormEvent) => {
        e.preventDefault();
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
    };

    return (
        <motion.div 
            className="tab-content"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
        >
            <h2 className="tab-title">Security Settings</h2>
            
            <div className="settings-layout">
                {/* Left col */}
                <div style={{ flex: 2, display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <div className="settings-section">
                        <h3 className="section-label"><Key size={18} style={{marginRight: 8, verticalAlign: 'text-bottom'}}/> Change Password</h3>
                        <form onSubmit={handlePassChange}>
                            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                                <label className="kl-label" style={{ marginBottom: 8, display: 'block' }}>Current Password</label>
                                <input type="password" className="form-input" required style={{ width: '100%' }} />
                            </div>
                            <div className="form-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                                <div className="form-group">
                                    <label className="kl-label" style={{ marginBottom: 8, display: 'block' }}>New Password</label>
                                    <input type="password" className="form-input" required style={{ width: '100%' }} />
                                </div>
                                <div className="form-group">
                                    <label className="kl-label" style={{ marginBottom: 8, display: 'block' }}>Confirm Password</label>
                                    <input type="password" className="form-input" required style={{ width: '100%' }} />
                                </div>
                            </div>
                            <div className="password-strength" style={{ marginTop: '1rem' }}>
                                <div className="str-bar" style={{ height: 6, background: '#e2e8f0', borderRadius: 10, width: '100%', overflow: 'hidden' }}>
                                    <div style={{ width: '60%', height: '100%', background: '#f59e0b' }} />
                                </div>
                                <span className="str-text" style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 6, display: 'block' }}>Strength: Medium. Include a number and symbol.</span>
                            </div>
                            <div style={{display: 'flex', alignItems: 'center'}}>
                                <button type="submit" className="ap-retrain-btn" style={{ width: 'auto', padding: '0.82rem 2rem', marginTop: '1.5rem' }}>Update Password</button>
                                {saved && <span className="save-success-msg" style={{ marginLeft: '1rem', marginTop: '1.5rem', color: '#10b981', fontWeight: 600 }}><CheckCircle size={16}/> Changed</span>}
                            </div>
                        </form>
                    </div>

                    <div className="settings-section">
                        <h3 className="section-label"><Globe size={18} style={{marginRight: 8, verticalAlign: 'text-bottom'}}/> API & Access Security</h3>
                        <div className="api-key-box" style={{ background: '#0f172a', padding: '1.25rem', borderRadius: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <code style={{ color: '#fff', fontSize: '0.9rem' }}>{showKey ? 'creditiq_sk_live_28374h89h2348923h4' : 'creditiq_sk_live_******************'}</code>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                <button className="btn-copy" style={{ background: 'rgba(255,255,255,0.1)', color: '#fff', padding: '0.4rem 0.8rem', borderRadius: 6, border: '1px solid rgba(255,255,255,0.1)' }} onClick={() => setShowKey(!showKey)}>{showKey ? 'Hide' : 'Reveal'}</button>
                                <button className="btn-copy ap-btn-regen" style={{ background: '#0d9488', color: '#fff', padding: '0.4rem 0.8rem', borderRadius: 6, border: 'none' }}><RefreshCw size={12}/> Regen</button>
                            </div>
                        </div>
                        <p className="security-note" style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.75rem' }}>Use this key to authenticate external system webhooks.</p>
                    </div>
                </div>

                {/* Right col */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <div className="settings-section">
                        <h3 className="section-label"><ShieldCheck size={18} style={{marginRight: 8, verticalAlign: 'text-bottom'}}/> Security Preferences</h3>
                        <div className="setting-toggle-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 0', borderBottom: '1px solid #f1f5f9' }}>
                            <span style={{ fontWeight: 500, fontSize: '0.9rem' }}>Two-Factor Auth <br/><span style={{fontSize: '0.75rem', color: '#64748B'}}>{mfa ? 'Enabled' : 'Disabled'} via App</span></span>
                            <div className={`toggle-switch ${mfa ? 'active' : ''}`} onClick={() => setMfa(!mfa)}>
                                <div className="toggle-knob" />
                            </div>
                        </div>
                        <div className="setting-toggle-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 0' }}>
                            <span style={{ fontWeight: 500, fontSize: '0.9rem' }}>IP Restriction <br/><span style={{fontSize: '0.75rem', color: '#64748B'}}>Require VPN to login</span></span>
                            <div className={`toggle-switch ${ipRestrict ? 'active' : ''}`} onClick={() => setIpRestrict(!ipRestrict)}>
                                <div className="toggle-knob" />
                            </div>
                        </div>
                    </div>

                    <div className="settings-section" style={{flex: 1}}>
                        <h3 className="section-label"><Monitor size={18} style={{marginRight: 8, verticalAlign: 'text-bottom'}}/> Session Management</h3>
                        <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                            <label className="kl-label" style={{ marginBottom: 8, display: 'block' }}>Auto-Logout Timeout</label>
                            <select className="form-input" value={sessionTimeout} onChange={e => setSessionTimeout(e.target.value)} style={{ width: '100%' }}>
                                <option value="15m">15 Minutes</option>
                                <option value="30m">30 Minutes</option>
                                <option value="1h">1 Hour</option>
                            </select>
                        </div>
                        
                        <div className="active-session" style={{ background: '#f8fafc', padding: '1rem', borderRadius: 12, display: 'flex', gap: '12px', alignItems: 'center' }}>
                            <div className="session-icon" style={{ background: '#fff', color: '#0d9488', padding: 8, borderRadius: 8, border: '1px solid #e2e8f0' }}><Monitor size={16}/></div>
                            <div className="session-info" style={{ display: 'flex', flexDirection: 'column' }}>
                                <strong style={{ fontSize: '0.85rem' }}>Current Session</strong>
                                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Windows • Chrome</span>
                            </div>
                            <div className="session-status" style={{ marginLeft: 'auto', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', fontSize: '0.7rem', fontWeight: 700, padding: '2px 8px', borderRadius: 20 }}>Active</div>
                        </div>

                        <button className="sidebar-logout" style={{ marginTop: '1.5rem', justifyContent: 'center' }} onClick={logout}>
                            <LogOut size={16} /> Logout all devices
                        </button>
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

/* ─── Admin Dashboard ─────────────────────────────────────────── */
const AdminDashboard: React.FC = () => {
    const { user, logout } = useAuth();
    const [activeTab, setActiveTab] = useState('operations');
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const [rbacRole, setRbacRole] = useState('Admin');

    const sidebarItems = [
        { id: 'operations', label: 'Operations', icon: LayoutDashboard },
        { id: 'admin',      label: 'Admin Panel', icon: Shield },
        { id: 'users',      label: 'Users',      icon: Users },
        { id: 'history',    label: 'History',    icon: History },
    ];

    const renderContent = () => {
        switch (activeTab) {
            case 'operations':
                return (
                    <motion.div 
                        className="tab-content-full" 
                        style={{ padding: 0 }}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.4 }}
                    >
                        <NewAnalysis hideNavbar={true} />
                    </motion.div>
                );
            case 'admin':
                return (
                    <div className="tab-content ap-enterprise">
                        <h2 className="tab-title">Executive Overview</h2>

                        {/* ── TOP METRIC CARDS ── */}
                        <div className="ap-metric-row">
                            <DashboardCard 
                                title="Total Analyses" 
                                value="1,284" 
                                delta="+12% vs last month" 
                                icon={<FileText size={22}/>} 
                                color="#0d9488" 
                                bg="rgba(13, 148, 136, 0.1)" 
                                delay={0.1}
                            />
                            <DashboardCard 
                                title="Active Users" 
                                value="38" 
                                delta="3 teams currently active" 
                                icon={<Users size={22}/>} 
                                color="#0891B2" 
                                bg="rgba(8, 145, 178, 0.1)" 
                                delay={0.2}
                            />
                            <DashboardCard 
                                title="Fraud Alerts" 
                                value="7" 
                                delta="High priority alerts" 
                                icon={<AlertTriangle size={22}/>} 
                                color="#DC2626" 
                                bg="rgba(220, 38, 38, 0.1)" 
                                delay={0.3}
                            />
                            <DashboardCard 
                                title="API Requests" 
                                value="48.2K" 
                                delta="Within safe limits" 
                                icon={<BarChart3 size={22}/>} 
                                color="#0891b2" 
                                bg="rgba(8, 145, 178, 0.1)" 
                                delay={0.4}
                            />
                        </div>

                        {/* ── ROW 2: SECURITY + API ── */}
                        <div className="ap-two-col">
                            <ChartSection 
                                title="API Usage Distribution" 
                                subtitle="Requests per endpoint (Last 24h)"
                                data={[
                                    { label: '/api/upload', value: 284, color: '#0d9488' },
                                    { label: '/api/analyze', value: 196, color: '#0891B2' },
                                    { label: '/api/fraud', value: 142, color: '#DC2626' },
                                    { label: '/api/cam/generate', value: 89, color: '#0891b2' },
                                ]}
                                type="bar"
                            />

                            <motion.div 
                                className="ap-card"
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ duration: 0.5, delay: 0.2 }}
                            >
                                <div className="ap-card-header">
                                    <Lock size={18} /> Governance & Access
                                </div>
                                {[
                                    { label: 'Two-Factor Authentication', active: true },
                                    { label: 'VPN Restriction (Encrypted)', active: false },
                                    { label: 'Session Auto-Timeout', active: true },
                                ].map(({ label, active }) => (
                                    <div key={label} className="ap-toggle-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.85rem 0', borderBottom: '1px solid #f1f5f9' }}>
                                        <span style={{ fontSize: '0.9rem', fontWeight: 500, color: '#334155' }}>{label}</span>
                                        <div className={`toggle-switch ${active ? 'active' : ''}`}>
                                            <div className="toggle-knob" />
                                        </div>
                                    </div>
                                ))}
                                <div className="ap-divider" style={{ margin: '1.5rem 0' }} />
                                <div className="ap-card-subheader" style={{ color: '#64748b', fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', marginBottom: '1rem' }}><Shield size={14}/> Role-Based Access Control</div>
                                <div className="ap-rbac-pills" style={{ display: 'flex', gap: '8px' }}>
                                    {['Admin', 'Analyst', 'Viewer'].map(role => (
                                        <motion.button
                                            key={role}
                                            className={`ap-role-pill ${rbacRole === role ? 'ap-role-pill-active' : ''}`}
                                            onClick={() => setRbacRole(role)}
                                            whileHover={{ y: -2 }}
                                            whileTap={{ scale: 0.95 }}
                                            style={{ 
                                                padding: '0.5rem 1.25rem', 
                                                borderRadius: 20, 
                                                border: rbacRole === role ? 'none' : '1.5px solid #e2e8f0',
                                                background: rbacRole === role ? '#0d3b38' : '#fff',
                                                color: rbacRole === role ? '#fff' : '#64748b',
                                                fontWeight: 600,
                                                fontSize: '0.8rem',
                                                cursor: 'pointer'
                                            }}
                                        >{role}</motion.button>
                                    ))}
                                </div>
                            </motion.div>
                        </div>

                        {/* ── ROW 3: FRAUD MONITORING + AI MODEL ── */}
                        <div className="ap-two-col">
                            {/* FRAUD MONITORING */}
                            <motion.div 
                                className="ap-card"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: 0.3 }}
                            >
                                <div className="ap-card-header"><AlertTriangle size={18}/> Active Risk Monitoring</div>
                                <div className="ap-fraud-list" style={{ display: 'flex', flexDirection: 'column' }}>
                                    {[
                                        { company: 'Reliance Exports Ltd.', issue: 'GST Mismatch (₹4.2Cr)', risk: 'High' },
                                        { company: 'Bharat Steel Works', issue: 'Circular Trading Detected', risk: 'High' },
                                        { company: 'Mumbai Textile Co.', issue: 'Promoter Default (MCA)', risk: 'Medium' },
                                        { company: 'Sunrise Agro Pvt.', issue: 'News Sentiment Negative', risk: 'Medium' },
                                        { company: 'Delta Infra Ltd.', issue: 'PAN-GST Name Mismatch', risk: 'Low' },
                                    ].map(({ company, issue, risk }) => (
                                        <div key={company} className="ap-fraud-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 0', borderBottom: '1px solid #f8fafc' }}>
                                            <div className="ap-fraud-info" style={{ display: 'flex', flexDirection: 'column' }}>
                                                <span className="ap-fraud-company" style={{ fontWeight: 700, fontSize: '0.92rem', color: '#1e293b' }}>{company}</span>
                                                <span className="ap-fraud-issue" style={{ fontSize: '0.8rem', color: '#64748b' }}>{issue}</span>
                                            </div>
                                            <span className={`ap-risk-badge ap-risk-${risk.toLowerCase()}`} style={{ 
                                                padding: '4px 12px', 
                                                borderRadius: 20, 
                                                fontSize: '0.7rem', 
                                                fontWeight: 800, 
                                                textTransform: 'uppercase',
                                                background: risk === 'High' ? 'rgba(220, 38, 38, 0.1)' : risk === 'Medium' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                                                color: risk === 'High' ? '#dc2626' : risk === 'Medium' ? '#d97706' : '#16a34a'
                                            }}>{risk}</span>
                                        </div>
                                    ))}
                                </div>
                            </motion.div>

                            {/* AI MODEL STATUS */}
                            <motion.div 
                                className="ap-card"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: 0.4 }}
                            >
                                <div className="ap-card-header"><Cpu size={18}/> CreditIQ Engine Status</div>
                                <div className="ap-model-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                                    {[
                                        { label: 'Model Status', value: 'Active', icon: <CheckCircle size={16} color="#10B981"/> },
                                        { label: 'Accuracy (AUC)', value: '94.2%', icon: <TrendingUp size={16} color="#0d9488"/> },
                                        { label: 'Last Trained', value: '22 Mar 2026', icon: <Clock size={16} color="#0891b2"/> },
                                        { label: 'Training Set', value: '50K Cases', icon: <Activity size={16} color="#0891B2"/> },
                                        { label: 'Fraud F1 Score', value: '0.918', icon: <Zap size={16} color="#f59e0b"/> },
                                        { label: 'Avg Inference', value: '1.4s', icon: <Monitor size={16} color="#64748B"/> },
                                    ].map(({ label, value, icon }) => (
                                        <div key={label} className="ap-model-stat" style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: 12, border: '1px solid #e2e8f0', display: 'flex', gap: '10px', alignItems: 'center' }}>
                                            <div className="ap-model-icon">{icon}</div>
                                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                <div className="ap-model-label" style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 600 }}>{label}</div>
                                                <div className="ap-model-value" style={{ fontSize: '0.9rem', fontWeight: 800, color: '#1e293b' }}>{value}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <motion.button 
                                    className="ap-retrain-btn"
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                >
                                    <RefreshCw size={14}/> Retrain Neural Engine
                                </motion.button>
                            </motion.div>
                        </div>

                        {/* ── ROW 4: SYSTEM LOGS ── */}
                        <motion.div 
                            className="ap-card ap-logs-card"
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5 }}
                        >
                            <div className="ap-card-header"><Bell size={18}/> Real-time System Audit</div>
                            <div className="ap-logs-list" style={{ maxHeight: 300, overflowY: 'auto' }}>
                                {[
                                    { time: '04:12 IST', user: 'admin@gmail.com', action: 'User login successful', type: 'info' },
                                    { time: '03:58 IST', user: 'System', action: 'Analysis #1287 completed for Tata Motors', type: 'success' },
                                    { time: '03:44 IST', user: 'System', action: 'Fraud alert raised — Bharat Steel Works (Circular Trading)', type: 'danger' },
                                    { time: '03:31 IST', user: 'ops@creditiq.ai', action: 'CAM document generated for Reliance Exports Ltd.', type: 'success' },
                                    { time: '03:20 IST', user: 'System', action: 'API rate limit warning — 92% of daily quota used', type: 'warn' },
                                    { time: '02:55 IST', user: 'admin@gmail.com', action: 'API key regenerated', type: 'info' },
                                ].map(({ time, user, action, type }, i) => (
                                    <div key={i} className={`ap-log-row ap-log-${type}`} style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 0', borderBottom: '1px solid #f8fafc' }}>
                                        <span className="ap-log-time" style={{ fontSize: '0.72rem', color: '#94a3b8', width: 70 }}>{time}</span>
                                        <span className={`ap-log-dot ap-log-dot-${type}`} style={{ width: 8, height: 8, borderRadius: '50%', background: type === 'info' ? '#0d9488' : type === 'success' ? '#10b981' : type === 'danger' ? '#ef4444' : '#f59e0b' }} />
                                        <span className="ap-log-user" style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', width: 130, overflow: 'hidden', textOverflow: 'ellipsis' }}>{user}</span>
                                        <span className="ap-log-action" style={{ fontSize: '0.85rem', color: '#334155' }}>{action}</span>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    </div>
                );
            case 'users':
                return (
                    <motion.div 
                        className="tab-content"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.4 }}
                    >
                        <h2 className="tab-title">User Management</h2>
                        <div className="ap-card" style={{ padding: 0, overflow: 'hidden' }}>
                            <table className="admin-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead style={{ background: '#f8fafc' }}>
                                    <tr>
                                        <th style={{ padding: '1rem 1.5rem', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', borderBottom: '1px solid #e2e8f0' }}>Name</th>
                                        <th style={{ padding: '1rem 1.5rem', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', borderBottom: '1px solid #e2e8f0' }}>Email</th>
                                        <th style={{ padding: '1rem 1.5rem', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', borderBottom: '1px solid #e2e8f0' }}>Role</th>
                                        <th style={{ padding: '1rem 1.5rem', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', borderBottom: '1px solid #e2e8f0' }}>Status</th>
                                        <th style={{ padding: '1rem 1.5rem', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', borderBottom: '1px solid #e2e8f0' }}>Last Login</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                                        <td style={{ padding: '1rem 1.5rem' }}>
                                            <div className="user-cell" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                <div className="user-avatar" style={{ width: 32, height: 32, borderRadius: '50%', background: '#0d3b38', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.8rem' }}>S</div>
                                                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>System Admin</span>
                                            </div>
                                        </td>
                                        <td style={{ padding: '1rem 1.5rem', fontSize: '0.88rem', color: '#475569' }}>admin@creditiq.ai</td>
                                        <td style={{ padding: '1rem 1.5rem' }}><span style={{ padding: '2px 10px', borderRadius: 20, background: 'rgba(13, 148, 136, 0.1)', color: '#0d9488', fontSize: '0.72rem', fontWeight: 700 }}>Super Admin</span></td>
                                        <td style={{ padding: '1rem 1.5rem' }}><span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981', fontSize: '0.8rem', fontWeight: 600 }}><div style={{ width: 8, height: 8, background: '#10b981', borderRadius: '50%' }} /> Online</span></td>
                                        <td style={{ padding: '1rem 1.5rem', fontSize: '0.85rem', color: '#64748b' }}>Just now</td>
                                    </tr>
                                    <tr>
                                        <td style={{ padding: '1rem 1.5rem' }}>
                                            <div className="user-cell" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                <div className="user-avatar" style={{ width: 32, height: 32, borderRadius: '50%', background: '#14b8a6', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.8rem' }}>O</div>
                                                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Operations Lead</span>
                                            </div>
                                        </td>
                                        <td style={{ padding: '1rem 1.5rem', fontSize: '0.88rem', color: '#475569' }}>ops@creditiq.ai</td>
                                        <td style={{ padding: '1rem 1.5rem' }}><span style={{ padding: '2px 10px', borderRadius: 20, background: 'rgba(20, 184, 166, 0.1)', color: '#14b8a6', fontSize: '0.72rem', fontWeight: 700 }}>Editor</span></td>
                                        <td style={{ padding: '1rem 1.5rem' }}><span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f59e0b', fontSize: '0.8rem', fontWeight: 600 }}><div style={{ width: 8, height: 8, background: '#f59e0b', borderRadius: '50%' }} /> Away</span></td>
                                        <td style={{ padding: '1rem 1.5rem', fontSize: '0.85rem', color: '#64748b' }}>2 hours ago</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </motion.div>
                );
            case 'history':
                return (
                    <motion.div 
                        className="tab-content-full"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.4 }}
                    >
                        <HistoryPage hideNavbar={true} />
                    </motion.div>
                );
            case 'profile':
                return <ProfileSettings user={user} />;
            case 'security':
                return <SecuritySettings />;
            default:
                return <div>Select a section</div>;
        }
    };

    return (
        <div className="admin-layout">
            <Sidebar 
                items={sidebarItems}
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                logout={logout}
            />
            
            <main className="admin-main">
                <header className="admin-header">
                    <div className="search-bar">
                        <Search size={18} color="#94a3b8" />
                        <input type="text" placeholder="Search appraisals, clients, or logs..." />
                    </div>
                    
                    <div className="admin-profile" onClick={() => setDropdownOpen(!dropdownOpen)}>
                        <div className="profile-info">
                            <span className="profile-name">{user?.name || 'CreditIQ Admin'}</span>
                            <span className="profile-role">{user?.role?.toUpperCase() || 'SYSTEM'}</span>
                        </div>
                        <div className="profile-avatar">{user?.name?.[0]?.toUpperCase() || 'A'}</div>
                        <ChevronDown size={14} className={`dropdown-arrow ${dropdownOpen ? 'open' : ''}`} />

                        <AnimatePresence>
                            {dropdownOpen && (
                                <motion.div 
                                    className="profile-dropdown" 
                                    onClick={(e) => e.stopPropagation()}
                                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                                    transition={{ duration: 0.2 }}
                                >
                                    <div className="dropdown-header">
                                        <div className="dropdown-avatar-lg">{user?.name?.[0]?.toUpperCase() || 'A'}</div>
                                        <div className="dropdown-user-details">
                                            <span className="dropdown-name">{user?.name || 'System Administrator'}</span>
                                            <span className="dropdown-email">{user?.email || 'admin@creditiq.ai'}</span>
                                            <span className="dropdown-role-badge">{user?.role?.toUpperCase() || 'SUPER ADMIN'}</span>
                                        </div>
                                    </div>
                                    <div className="dropdown-divider"></div>

                                    <div className="dropdown-section">
                                        <span className="dropdown-section-title">Account</span>
                                        <button className="dropdown-item" onClick={() => { setActiveTab('profile'); setDropdownOpen(false); }}><User size={14} /> Profile Settings</button>
                                        <button className="dropdown-item" onClick={() => { setActiveTab('security'); setDropdownOpen(false); }}><Lock size={14} /> Security Settings</button>
                                    </div>
                                    <div className="dropdown-divider"></div>

                                    <div className="dropdown-section">
                                        <span className="dropdown-section-title">System Status</span>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem' }}>
                                                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748b' }}><Cpu size={12} /> AI Engine</span>
                                                <span style={{ color: '#10b981', fontWeight: 700 }}>Online</span>
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem' }}>
                                                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748b' }}><Globe size={12} /> API Core</span>
                                                <span style={{ color: '#10b981', fontWeight: 700 }}>Stable</span>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div className="dropdown-divider"></div>
                                    <button className="dropdown-item dropdown-logout" onClick={() => { setDropdownOpen(false); logout(); }}>
                                        <LogOut size={14} /> Sign Out
                                    </button>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </header>
                
                <div className="admin-content-area">
                    {renderContent()}
                </div>
            </main>
            <Chatbot />
        </div>
    );
};

export default AdminDashboard;
