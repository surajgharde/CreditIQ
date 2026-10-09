import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
    Zap, Send, Plus, Trash2, Power, CheckCircle, AlertTriangle,
    Building2, User, Loader, Info
} from 'lucide-react';
import './Profile.css';
import api from '../services/apiConfig';
import { useAuth } from '../context/AuthContext';

interface TelegramLink {
    id: number;
    chat_id: number;
    company_id: number;
    company_name: string;
    label: string;
    is_active: boolean;
}

interface CompanyOption {
    id: number;
    company_name: string;
    cin_number?: string;
}

type Notice = { kind: 'ok' | 'err'; text: string } | null;

function Profile() {
    const { user } = useAuth();

    const [links, setLinks] = useState<TelegramLink[]>([]);
    const [companies, setCompanies] = useState<CompanyOption[]>([]);
    const [botUsername, setBotUsername] = useState<string | null>(null);
    const [configured, setConfigured] = useState(false);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [notice, setNotice] = useState<Notice>(null);

    const [chatId, setChatId] = useState('');
    const [companyId, setCompanyId] = useState('');
    const [label, setLabel] = useState('');

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [tg, co] = await Promise.all([
                api.get('/api/profile/telegram'),
                api.get('/api/profile/companies'),
            ]);
            setLinks(tg.data.links || []);
            setConfigured(!!tg.data.configured);
            setBotUsername(tg.data.bot_username || null);
            setCompanies(co.data.companies || []);
        } catch (err: any) {
            setNotice({ kind: 'err', text: err.userMessage || 'Could not load profile settings.' });
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const addLink = async (e: React.FormEvent) => {
        e.preventDefault();
        setNotice(null);

        const trimmed = chatId.trim();
        // Telegram chat IDs are integers and negative for group chats.
        if (!/^-?\d+$/.test(trimmed)) {
            setNotice({ kind: 'err', text: 'Chat ID must be a number. Ask the contact to send /whoami to the bot.' });
            return;
        }
        if (!companyId) {
            setNotice({ kind: 'err', text: 'Choose the company this chat should be limited to.' });
            return;
        }

        setSaving(true);
        try {
            const { data } = await api.post('/api/profile/telegram', {
                chat_id: Number(trimmed),
                company_id: Number(companyId),
                label: label.trim(),
            });
            setChatId(''); setLabel('');
            setNotice({
                kind: 'ok',
                text: data.status === 'updated'
                    ? `Chat ${trimmed} re-pointed to ${data.link.company_name}.`
                    : `Chat ${trimmed} linked to ${data.link.company_name}.`,
            });
            await load();
        } catch (err: any) {
            setNotice({ kind: 'err', text: err.userMessage || 'Could not save the link.' });
        } finally {
            setSaving(false);
        }
    };

    const toggle = async (link: TelegramLink) => {
        try {
            await api.patch(`/api/profile/telegram/${link.id}?active=${!link.is_active}`);
            await load();
        } catch (err: any) {
            setNotice({ kind: 'err', text: err.userMessage || 'Could not update the link.' });
        }
    };

    const remove = async (link: TelegramLink) => {
        try {
            await api.delete(`/api/profile/telegram/${link.id}`);
            setNotice({ kind: 'ok', text: `Removed chat ${link.chat_id}.` });
            await load();
        } catch (err: any) {
            setNotice({ kind: 'err', text: err.userMessage || 'Could not remove the link.' });
        }
    };

    const sendTest = async (link: TelegramLink) => {
        setNotice(null);
        try {
            await api.post(`/api/profile/telegram/${link.id}/test`);
            setNotice({ kind: 'ok', text: `Test message sent to chat ${link.chat_id}.` });
        } catch (err: any) {
            setNotice({ kind: 'err', text: err.userMessage || 'Could not send the test message.' });
        }
    };

    return (
        <div className="profile-page">
            <nav className="profile-navbar">
                <Link to="/" className="logo-container">
                    <Zap size={22} />
                    CreditIQ
                </Link>
                <div className="nav-center-title">
                    <User size={16} />
                    Profile &amp; Settings
                </div>
                <Link to="/history" className="creditiq-btn creditiq-btn--ghost btn-sm">
                    Back to history
                </Link>
            </nav>

            <div className="profile-container">
                <section className="profile-card">
                    <h2 className="card-title"><User size={18} /> Account</h2>
                    <div className="account-grid">
                        <div>
                            <span className="field-label">Signed in as</span>
                            <span className="field-value">{user?.email || 'not signed in'}</span>
                        </div>
                        <div>
                            <span className="field-label">Name</span>
                            <span className="field-value">{user?.name || '—'}</span>
                        </div>
                        <div>
                            <span className="field-label">Role</span>
                            <span className="field-value">{user?.role || '—'}</span>
                        </div>
                    </div>
                </section>

                <section className="profile-card">
                    <h2 className="card-title"><Send size={18} /> Telegram chat access</h2>

                    <p className="card-help">
                        Link a Telegram chat to one company. The bot answers that chat
                        <strong> only about that company</strong> — nothing about any other
                        borrower.
                    </p>

                    {!configured && (
                        <div className="banner banner-warn">
                            <AlertTriangle size={16} />
                            <span>
                                No Telegram bot token is configured on the server. Set
                                <code> TELEGRAM_BOT_TOKEN </code> in <code>backend/.env</code>.
                            </span>
                        </div>
                    )}

                    {configured && (
                        <div className="banner banner-info">
                            <Info size={16} />
                            <span>
                                Ask the contact to open{' '}
                                {botUsername
                                    ? <a href={`https://t.me/${botUsername}`} target="_blank" rel="noreferrer">@{botUsername}</a>
                                    : 'the bot'}
                                {' '}and send <code>/whoami</code>. It replies with their chat ID — paste it below.
                                A bot cannot message someone who has never written to it first.
                            </span>
                        </div>
                    )}

                    {notice && (
                        <div className={`banner ${notice.kind === 'ok' ? 'banner-ok' : 'banner-err'}`}>
                            {notice.kind === 'ok' ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
                            <span>{notice.text}</span>
                        </div>
                    )}

                    <form className="link-form" onSubmit={addLink}>
                        <div className="form-row">
                            <label className="form-field">
                                <span className="field-label">Telegram chat ID</span>
                                <input
                                    type="text"
                                    inputMode="numeric"
                                    placeholder="e.g. 123456789"
                                    value={chatId}
                                    onChange={e => setChatId(e.target.value)}
                                />
                            </label>

                            <label className="form-field">
                                <span className="field-label">Company</span>
                                <select value={companyId} onChange={e => setCompanyId(e.target.value)}>
                                    <option value="">Select a company…</option>
                                    {companies.map(c => (
                                        <option key={c.id} value={c.id}>
                                            {c.company_name}{c.cin_number ? ` — ${c.cin_number}` : ''}
                                        </option>
                                    ))}
                                </select>
                            </label>

                            <label className="form-field">
                                <span className="field-label">Label (optional)</span>
                                <input
                                    type="text"
                                    placeholder="Contact name"
                                    value={label}
                                    onChange={e => setLabel(e.target.value)}
                                />
                            </label>
                        </div>

                        <button
                            type="submit"
                            className="creditiq-btn creditiq-btn--primary"
                            disabled={saving || companies.length === 0}
                        >
                            {saving ? <Loader size={15} className="spin" /> : <Plus size={15} />}
                            {saving ? 'Saving…' : 'Link chat'}
                        </button>

                        {companies.length === 0 && !loading && (
                            <span className="inline-note">
                                No companies yet — run an analysis first.
                            </span>
                        )}
                    </form>

                    <div className="link-list">
                        {loading ? (
                            <div className="empty-state"><Loader size={18} className="spin" /> Loading…</div>
                        ) : links.length === 0 ? (
                            <div className="empty-state">
                                No chats linked yet. Until a chat is linked, the bot shares nothing.
                            </div>
                        ) : (
                            <table className="link-table">
                                <thead>
                                    <tr>
                                        <th>Chat ID</th>
                                        <th>Company</th>
                                        <th>Label</th>
                                        <th>State</th>
                                        <th className="col-actions">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {links.map(link => (
                                        <tr key={link.id} className={link.is_active ? '' : 'row-inactive'}>
                                            <td className="mono">{link.chat_id}</td>
                                            <td>
                                                <Building2 size={13} /> {link.company_name}
                                            </td>
                                            <td>{link.label || '—'}</td>
                                            <td>
                                                <span className={`pill ${link.is_active ? 'pill-on' : 'pill-off'}`}>
                                                    {link.is_active ? 'Active' : 'Disabled'}
                                                </span>
                                            </td>
                                            <td className="col-actions">
                                                <button
                                                    className="icon-btn"
                                                    title="Send a test message"
                                                    onClick={() => sendTest(link)}
                                                    disabled={!configured}
                                                >
                                                    <Send size={14} />
                                                </button>
                                                <button
                                                    className="icon-btn"
                                                    title={link.is_active ? 'Disable' : 'Enable'}
                                                    onClick={() => toggle(link)}
                                                >
                                                    <Power size={14} />
                                                </button>
                                                <button
                                                    className="icon-btn icon-btn--danger"
                                                    title="Remove"
                                                    onClick={() => remove(link)}
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </section>
            </div>
        </div>
    );
}

export default Profile;
