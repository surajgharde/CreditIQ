import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Mail, Lock, Eye, EyeOff, Loader2, ArrowRight,
  ShieldCheck, Zap, Activity, ArrowLeft, Shield
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './Login.css';

/* ─── animation variants ──────────────────────────────────────── */
const panelVariants: any = {
  hidden: { opacity: 0, x: -40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] } },
};

const cardVariants: any = {
  hidden: { opacity: 0, y: 32, scale: 0.97 },
  visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.08 } },
};

const itemVariants: any = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.15 + i * 0.07 },
  }),
};

const FEATURES = [
  { icon: <Zap size={17} />, label: 'Real-time AI credit analysis & scoring' },
  { icon: <ShieldCheck size={17} />, label: 'Automated fraud detection engine' },
  { icon: <Activity size={17} />, label: 'Deep financial insights & CAM generation' },
];

/* ─── STATS BAR ───────────────────────────────────────────────── */
const STATS = [
  { value: '2 hrs', label: 'CAM Speed' },
  { value: '94%+', label: 'Fraud Rate' },
  { value: '8,400+', label: 'Analysed' },
];

/* ═══════════════════════════════════════════════════════════════ */
const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [focusedField, setFocusedField] = useState<'email' | 'password' | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate('/admin-dashboard');
    } catch (err: any) {
      setError(err.message || 'Invalid credentials. Please try again.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="kl-root">

      {/* ══════════════ LEFT BRANDING PANEL ══════════════ */}
      <motion.aside
        className="kl-panel"
        variants={panelVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Orbs */}
        <div className="kl-orb kl-orb--1" />
        <div className="kl-orb kl-orb--2" />
        {/* Grid */}
        <div className="kl-grid" aria-hidden />

        <div className="kl-panel__content">
          {/* Logo */}
          <Link to="/" className="kl-logo">
            <motion.div
              className="kl-logo__icon"
              whileHover={{ rotate: 15, scale: 1.1 }}
              transition={{ type: 'spring', stiffness: 340 }}
            >
              <Zap size={17} fill="currentColor" stroke="none" />
            </motion.div>
            <span className="kl-logo__text">CreditIQ</span>
          </Link>

          {/* Main copy */}
          <div className="kl-panel__main">
            <motion.h2
              className="kl-panel__headline"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
            >
              Enterprise Credit<br />
              <span className="kl-panel__headline--gradient">Intelligence</span>
            </motion.h2>

            <motion.p
              className="kl-panel__sub"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            >
              Streamline risk assessment and fraud detection with our
              advanced AI decision engine — built for Indian finance.
            </motion.p>

            {/* Feature list */}
            <motion.ul
              className="kl-featurelist"
              initial="hidden"
              animate="visible"
              variants={{ visible: { transition: { staggerChildren: 0.1, delayChildren: 0.45 } } }}
            >
              {FEATURES.map(({ icon, label }, i) => (
                <motion.li
                  key={i}
                  className="kl-featurelist__item"
                  variants={{ hidden: { opacity: 0, x: -16 }, visible: { opacity: 1, x: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } } }}
                >
                  <span className="kl-featurelist__icon">{icon}</span>
                  <span>{label}</span>
                </motion.li>
              ))}
            </motion.ul>

            {/* Stats */}
            <motion.div
              className="kl-panel__stats"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8, duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
            >
              {STATS.map(({ value, label }, i) => (
                <div key={label} className="kl-panel__stat">
                  {i > 0 && <div className="kl-panel__stat-div" />}
                  <span className="kl-panel__stat-val">{value}</span>
                  <span className="kl-panel__stat-lbl">{label}</span>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Footer */}
          <div className="kl-panel__footer">
            <Shield size={12} /> Secure Environment &nbsp;·&nbsp; AES-256 Encryption &nbsp;·&nbsp; RBI-Compliant
          </div>
        </div>
      </motion.aside>

      {/* ══════════════ RIGHT LOGIN PANEL ══════════════ */}
      <div className="kl-form-side">

        {/* Back link */}
        <motion.div
          className="kl-back"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Link to="/" className="kl-back__link">
            <ArrowLeft size={14} /> Back to Home
          </Link>
        </motion.div>

        {/* Login Card */}
        <motion.div
          className="kl-card"
          variants={cardVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Card top accent bar */}
          <div className="kl-card__accent" />

          {/* Header */}
          <motion.div className="kl-card__header" custom={0} variants={itemVariants} initial="hidden" animate="visible">
            <div className="kl-card__logo-ring">
              <Zap size={22} fill="currentColor" stroke="none" />
            </div>
            <h1 className="kl-card__title">Welcome Back</h1>
            <p className="kl-card__subtitle">Sign in to your CreditIQ admin account</p>
          </motion.div>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                className="kl-error"
                initial={{ opacity: 0, y: -8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -8, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <ShieldCheck size={15} /> {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Form */}
          <motion.form
            onSubmit={handleSubmit}
            className="kl-form"
            custom={1}
            variants={itemVariants}
            initial="hidden"
            animate="visible"
          >
            {/* Email */}
            <motion.div className="kl-field" custom={2} variants={itemVariants} initial="hidden" animate="visible">
              <label className="kl-label" htmlFor="login-email">Email Address</label>
              <div className={`kl-input-wrap${focusedField === 'email' ? ' kl-input-wrap--focused' : ''}`}>
                <Mail className="kl-input-icon" size={17} />
                <input
                  id="login-email"
                  type="email"
                  className="kl-input"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  onFocus={() => setFocusedField('email')}
                  onBlur={() => setFocusedField(null)}
                  placeholder="admin@creditiq.ai"
                  required
                  autoComplete="email"
                />
              </div>
            </motion.div>

            {/* Password */}
            <motion.div className="kl-field" custom={3} variants={itemVariants} initial="hidden" animate="visible">
              <label className="kl-label" htmlFor="login-password">Password</label>
              <div className={`kl-input-wrap${focusedField === 'password' ? ' kl-input-wrap--focused' : ''}`}>
                <Lock className="kl-input-icon" size={17} />
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  className="kl-input kl-input--password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => setFocusedField(null)}
                  placeholder="••••••••••••"
                  required
                  autoComplete="current-password"
                />
                <motion.button
                  type="button"
                  className="kl-eye-btn"
                  onClick={() => setShowPassword(v => !v)}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </motion.button>
              </div>
            </motion.div>

            {/* Submit */}
            <motion.div custom={4} variants={itemVariants} initial="hidden" animate="visible">
              <motion.button
                type="submit"
                className="kl-submit-btn"
                disabled={isSubmitting}
                whileHover={isSubmitting ? {} : { scale: 1.02, y: -2 }}
                whileTap={isSubmitting ? {} : { scale: 0.98 }}
                transition={{ type: 'spring', stiffness: 340, damping: 22 }}
              >
                {isSubmitting ? (
                  <>
                    <motion.span
                      animate={{ rotate: 360 }}
                      transition={{ duration: 0.9, repeat: Infinity, ease: 'linear' }}
                      style={{ display: 'inline-flex' }}
                    >
                      <Loader2 size={18} />
                    </motion.span>
                    Authenticating…
                  </>
                ) : (
                  <>Sign In <ArrowRight size={18} /></>
                )}
              </motion.button>
            </motion.div>
          </motion.form>

          {/* Card footer note */}
          <motion.p
            className="kl-card__note"
            custom={5}
            variants={itemVariants}
            initial="hidden"
            animate="visible"
          >
            Protected by enterprise-grade security
          </motion.p>
        </motion.div>

        {/* Bottom ribbon */}
        <motion.div
          className="kl-ribbon"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
        >
          {['RBI-Compliant', 'XGBoost Scoring', 'FinBERT NLP', 'Cohere CAM'].map((t, i) => (
            <span key={t} className="kl-ribbon__pill">
              {i > 0 && <span className="kl-ribbon__sep">·</span>} {t}
            </span>
          ))}
        </motion.div>
      </div>
    </div>
  );
};

export default Login;
