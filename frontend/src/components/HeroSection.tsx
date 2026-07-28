import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, PlayCircle, Shield, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface HeroSectionProps {
  onScrollTo: (id: string) => void;
}

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1], delay },
  }),
};

const STAT_ITEMS = [
  { value: '2 hrs', label: 'CAM Generation' },
  { value: '94%+', label: 'Fraud Accuracy' },
  { value: '20%+', label: 'Better Default Prediction' },
];

export default function HeroSection({ onScrollTo }: HeroSectionProps) {
  const { user } = useAuth();

  return (
    <section className="creditiq-hero">
      {/* Background gradient orbs */}
      <div className="creditiq-hero__orb creditiq-hero__orb--1" />
      <div className="creditiq-hero__orb creditiq-hero__orb--2" />
      <div className="creditiq-hero__orb creditiq-hero__orb--3" />

      {/* Dot grid overlay */}
      <div className="creditiq-hero__grid" aria-hidden />

      <div className="creditiq-container creditiq-hero__content">
        {/* Badge */}
        <motion.div
          className="creditiq-hero__badge"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0}
        >
          <Shield size={14} />
          India's First RBI-Compliant AI Credit Platform
        </motion.div>

        {/* Headline */}
        <motion.h1
          className="creditiq-hero__headline"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.1}
        >
          Credit Intelligence<br />
          <span className="creditiq-hero__headline--gradient">That Never <br className="creditiq-hero__br-mobile" />Guesses Wrong</span>
        </motion.h1>

        {/* Subtext */}
        <motion.p
          className="creditiq-hero__subtext"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.2}
        >
          CreditIQ reads every document, detects every fraud, explains every decision
          and writes the full Credit Appraisal Memo — automatically in 2 hours.
        </motion.p>

        {/* CTAs */}
        <motion.div
          className="creditiq-hero__actions"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.3}
        >
          {user ? (
            <motion.div whileHover={{ scale: 1.04, y: -2 }} whileTap={{ scale: 0.97 }}>
              <Link to="/newanalysis" className="creditiq-btn creditiq-btn--primary creditiq-btn--lg">
                Start Credit Analysis <ArrowRight size={18} />
              </Link>
            </motion.div>
          ) : (
            <motion.div whileHover={{ scale: 1.04, y: -2 }} whileTap={{ scale: 0.97 }}>
              <Link to="/login" className="creditiq-btn creditiq-btn--primary creditiq-btn--lg">
                Login to CreditIQ AI <ArrowRight size={18} />
              </Link>
            </motion.div>
          )}

          <motion.button
            className="creditiq-btn creditiq-btn--glass creditiq-btn--lg"
            onClick={() => onScrollTo('product')}
            whileHover={{ scale: 1.04, y: -2 }}
            whileTap={{ scale: 0.97 }}
          >
            <PlayCircle size={18} /> See How It Works
          </motion.button>
        </motion.div>

        {/* Stats bar */}
        <motion.div
          className="creditiq-hero__stats"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.45}
        >
          {STAT_ITEMS.map(({ value, label }, i) => (
            <div key={label} className="creditiq-hero__stat">
              {i > 0 && <div className="creditiq-hero__stat-divider" />}
              <span className="creditiq-hero__stat-value">{value}</span>
              <span className="creditiq-hero__stat-label">{label}</span>
            </div>
          ))}
        </motion.div>

        {/* Dashboard Mockup */}
        <motion.div
          className="creditiq-hero__mockup-wrap"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.55}
        >
          <div className="creditiq-hero__mockup">
            {/* Window chrome */}
            <div className="creditiq-mockup__chrome">
              <span className="creditiq-mockup__dot creditiq-mockup__dot--red" />
              <span className="creditiq-mockup__dot creditiq-mockup__dot--yellow" />
              <span className="creditiq-mockup__dot creditiq-mockup__dot--green" />
              <span className="creditiq-mockup__title">CreditIQ — Credit Analysis Dashboard</span>
            </div>

            <div className="creditiq-mockup__body">
              {/* Sidebar */}
              <div className="creditiq-mockup__sidebar">
                {['Dashboard', 'New Analysis', 'History', 'Fraud Report', 'EWS'].map(item => (
                  <div key={item} className="creditiq-mockup__sidebar-item">{item}</div>
                ))}
              </div>

              {/* Main content */}
              <div className="creditiq-mockup__main">
                <div className="creditiq-mockup__row">
                  {[
                    { label: 'Risk Score', value: '78/100', color: '#22c55e' },
                    { label: 'Fraud Score', value: 'Low', color: '#14b8a6' },
                    { label: 'PD Rate', value: '4.2%', color: '#f59e0b' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="creditiq-mockup__kpi">
                      <span className="creditiq-mockup__kpi-label">{label}</span>
                      <span className="creditiq-mockup__kpi-value" style={{ color }}>{value}</span>
                    </div>
                  ))}
                </div>
                <div className="creditiq-mockup__chart">
                  <div className="creditiq-mockup__chart-title">Probability of Default — SHAP Breakdown</div>
                  <div className="creditiq-mockup__bars">
                    {[70, 45, 85, 55, 90, 38, 60].map((h, i) => (
                      <motion.div
                        key={i}
                        className="creditiq-mockup__bar"
                        style={{ height: `${h}%` }}
                        initial={{ scaleY: 0 }}
                        animate={{ scaleY: 1 }}
                        transition={{ delay: 0.7 + i * 0.07, duration: 0.5, ease: 'easeOut' }}
                      />
                    ))}
                  </div>
                </div>
                <div className="creditiq-mockup__status-row">
                  <div className="creditiq-mockup__status creditiq-mockup__status--green">✓ CAM Generated</div>
                  <div className="creditiq-mockup__status creditiq-mockup__status--blue">✓ Fraud Check Complete</div>
                  <div className="creditiq-mockup__status creditiq-mockup__status--purple">✓ RAG Retrieved</div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Scroll hint */}
        <motion.div
          className="creditiq-hero__scroll-hint"
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          onClick={() => onScrollTo('product')}
        >
          <ChevronDown size={22} />
        </motion.div>
      </div>
    </section>
  );
}
