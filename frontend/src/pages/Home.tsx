import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FileText, AlertTriangle, BarChart3,
  BookOpen, Shield, Zap, TrendingUp
} from 'lucide-react';
import Navbar from '../components/Navbar';
import HeroSection from '../components/HeroSection';
import FeatureCards from '../components/FeatureCards';
import './Home.css';

const NAV_ITEMS = [
  { id: 'product', label: 'Product' },
  { id: 'features', label: 'Features' },
  { id: 'research', label: 'Research' },
];

const fadeUp = (delay = 0): any => ({
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.65, ease: [0.16, 1, 0.3, 1], delay } },
});

const stagger: any = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.09 } },
};

const cardReveal: any = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] } },
};

function Home() {
  const [activeSection, setActiveSection] = useState('');

  useEffect(() => {
    const observers: IntersectionObserver[] = [];
    NAV_ITEMS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (!el) return;
      const obs = new IntersectionObserver(
        ([entry]) => { if (entry.isIntersecting) setActiveSection(id); },
        { rootMargin: '-40% 0px -55% 0px' }
      );
      obs.observe(el);
      observers.push(obs);
    });
    return () => observers.forEach(o => o.disconnect());
  }, []);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="creditiq-page">
      {/* ─── NAVBAR ─────────────────────────────────────────────── */}
      <Navbar activeSection={activeSection} onScrollTo={scrollTo} />

      <main>
        {/* ─── HERO ───────────────────────────────────────────────── */}
        <HeroSection onScrollTo={scrollTo} />

        {/* ─── TECH RIBBON ──────────────────────────────────────── */}
        <div className="creditiq-ribbon">
          <div className="creditiq-ribbon__inner">
            {['PdfTable', 'XGBoost', 'SHAP', 'LangChain', 'FinBERT', 'Cohere', 'ChromaDB', 'AWS Textract'].map(t => (
              <span key={t} className="creditiq-ribbon__item">{t}</span>
            ))}
          </div>
        </div>

        {/* ─── STATS ──────────────────────────────────────────────── */}
        <section className="creditiq-stats-section">
          <div className="creditiq-container">
            <motion.div
              className="creditiq-stats-grid"
              variants={stagger}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-60px' }}
            >
              {[
                { icon: <Zap size={26} />, value: '2 Hours', desc: 'CAM Generation vs. 5 Days Manual', color: '#14b8a6' },
                { icon: <Shield size={26} />, value: '94%+', desc: 'Fraud Detection Accuracy', color: '#10b981' },
                { icon: <TrendingUp size={26} />, value: '20%+', desc: 'Better Default Prediction via RAG', color: '#f59e0b' },
              ].map(({ icon, value, desc, color }) => (
                <motion.div
                  key={value}
                  className="creditiq-stat-card"
                  variants={cardReveal}
                  whileHover={{ y: -6, boxShadow: `0 20px 40px ${color}22` }}
                  transition={{ type: 'spring', stiffness: 280, damping: 20 }}
                >
                  <div className="creditiq-stat-card__icon" style={{ color, background: `${color}14` }}>
                    {icon}
                  </div>
                  <div className="creditiq-stat-card__value" style={{ color }}>{value}</div>
                  <div className="creditiq-stat-card__desc">{desc}</div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ─── PRODUCT ────────────────────────────────────────────── */}
        <section id="product" className="creditiq-section">
          <div className="creditiq-container">
            <motion.div
              className="creditiq-section__header"
              variants={fadeUp(0)}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-80px' }}
            >
              <div className="creditiq-section__label">PRODUCT</div>
              <h2 className="creditiq-section__title">End-to-End Credit Intelligence Platform</h2>
              <p className="creditiq-section__subtitle">
                CreditIQ automates the entire credit appraisal workflow — from document ingestion to
                final CAM generation — with full RBI compliance and explainability at every step.
              </p>
            </motion.div>

            <motion.div
              className="creditiq-workflow-grid"
              variants={stagger}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-60px' }}
            >
              {[
                { step: '01', icon: <FileText size={28} />, title: 'Upload Documents', desc: 'Balance sheets, bank statements, GST filings processed via AI-powered OCR engine.' },
                { step: '02', icon: <AlertTriangle size={28} />, title: 'Fraud Detection', desc: 'Cross-verifies GST data, circular trading patterns, and MCA promoter history.' },
                { step: '03', icon: <BarChart3 size={28} />, title: 'Risk Scoring', desc: 'XGBoost model calculates Probability of Default with SHAP-based explanations.' },
                { step: '04', icon: <FileText size={28} />, title: 'CAM Generation', desc: 'Cohere AI drafts a full Credit Appraisal Memo — RBI-compliant, audit-ready.' },
              ].map(({ step, icon, title, desc }) => (
                <motion.div
                  key={step}
                  className="creditiq-workflow-card"
                  variants={cardReveal}
                  whileHover={{ y: -8 }}
                  transition={{ type: 'spring', stiffness: 280, damping: 22 }}
                >
                  <div className="creditiq-workflow-card__step">{step}</div>
                  <div className="creditiq-workflow-card__icon">{icon}</div>
                  <h4 className="creditiq-workflow-card__title">{title}</h4>
                  <p className="creditiq-workflow-card__desc">{desc}</p>
                  <div className="creditiq-workflow-card__connector" />
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ─── FEATURES ───────────────────────────────────────────── */}
        <FeatureCards />

        {/* ─── RESEARCH ───────────────────────────────────────────── */}
        <section id="research" className="creditiq-section">
          <div className="creditiq-container">
            <motion.div
              className="creditiq-section__header"
              variants={fadeUp(0)}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-80px' }}
            >
              <div className="creditiq-section__label">RESEARCH</div>
              <h2 className="creditiq-section__title">Built on Peer-Reviewed AI Research</h2>
              <p className="creditiq-section__subtitle">
                Every CreditIQ engine is grounded in published research, fine-tuned for India's credit markets.
              </p>
            </motion.div>

            <motion.div
              className="creditiq-research-grid"
              variants={stagger}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-60px' }}
            >
              {[
                { model: 'XGBoost', badge: 'Scoring Engine', desc: 'Gradient-boosted trees trained on CIBIL + RBI NPA datasets. Achieves AUC 0.91 on Indian SME default prediction.', papers: '3 papers' },
                { model: 'SHAP', badge: 'Explainability', desc: 'SHapley Additive exPlanations provide regulator-grade reasoning for every credit decision, legally defensible under RBI guidelines.', papers: '2 papers' },
                { model: 'FinBERT', badge: 'NLP / Sentiment', desc: 'Domain-adapted BERT model for financial news. Fine-tuned on Indian market corpus to detect promoter risk signals.', papers: '4 papers' },
                { model: 'LangChain', badge: 'RAG Pipeline', desc: '4-level RAG framework: raw financials + risk signals + sector benchmarks + RBI regulatory context fed to Cohere.', papers: '2 papers' },
                { model: 'PdfTable', badge: 'Document AI', desc: 'Extracts structured financial tables from scanned PDFs without ML, enabling zero-shot document understanding.', papers: '1 paper' },
                { model: 'ChromaDB', badge: 'Vector Memory', desc: 'Stores sector benchmark embeddings and historical NPA case studies for real-time RAG retrieval during analysis.', papers: '1 paper' },
              ].map(({ model, badge, desc, papers }) => (
                <motion.div
                  key={model}
                  className="creditiq-research-card"
                  variants={cardReveal}
                  whileHover={{ y: -5 }}
                  transition={{ type: 'spring', stiffness: 280, damping: 22 }}
                >
                  <div className="creditiq-research-card__header">
                    <span className="creditiq-research-card__model">{model}</span>
                    <span className="creditiq-research-card__badge">{badge}</span>
                  </div>
                  <p className="creditiq-research-card__desc">{desc}</p>
                  <div className="creditiq-research-card__papers">
                    <BookOpen size={12} /> {papers}
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ─── POWERED BY ─────────────────────────────────────────── */}
        <section className="creditiq-powered">
          <div className="creditiq-container">
            <motion.div
              className="creditiq-powered__title"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              POWERED BY
            </motion.div>
            <motion.div
              className="creditiq-powered__logos"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.1 }}
            >
              {['PdfTable', 'XGBoost', 'SHAP', 'LangChain', 'FinBERT', 'Cohere', 'ChromaDB'].map(t => (
                <motion.div
                  key={t}
                  className="creditiq-powered__logo"
                  whileHover={{ scale: 1.08, color: '#0d3b38' }}
                  transition={{ type: 'spring', stiffness: 300 }}
                >
                  {t}
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ─── CTA BANNER ─────────────────────────────────────────── */}
        <section className="creditiq-cta">
          <div className="creditiq-cta__orb creditiq-cta__orb--1" />
          <div className="creditiq-cta__orb creditiq-cta__orb--2" />
          <div className="creditiq-container creditiq-cta__inner">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            >
              <h2 className="creditiq-cta__headline">
                Ready to transform your<br />credit appraisal process?
              </h2>
              <p className="creditiq-cta__sub">
                Join top-tier Indian financial institutions using CreditIQ's AI.
              </p>
              <div className="creditiq-cta__actions">
                <motion.div whileHover={{ scale: 1.05, y: -2 }} whileTap={{ scale: 0.97 }}>
                  <Link to="/login" className="creditiq-btn creditiq-btn--white creditiq-btn--lg">
                    Get Started Today
                  </Link>
                </motion.div>
                <motion.button
                  className="creditiq-btn creditiq-btn--outline-white creditiq-btn--lg"
                  onClick={() => scrollTo('product')}
                  whileHover={{ scale: 1.05, y: -2 }}
                  whileTap={{ scale: 0.97 }}
                >
                  Book a Demo
                </motion.button>
              </div>
            </motion.div>
          </div>
        </section>
      </main>

      {/* ─── FOOTER ─────────────────────────────────────────────── */}
      <footer className="creditiq-footer">
        <div className="creditiq-container creditiq-footer__inner">
          <div className="creditiq-logo">
            <div className="creditiq-logo__icon">
              <Zap size={16} fill="currentColor" stroke="none" />
            </div>
            <span className="creditiq-logo__text">CreditIQ</span>
          </div>
          <div className="creditiq-footer__links">
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Service</a>
            <a href="#">Compliance</a>
            <a href="#">Contact</a>
          </div>
          <div className="creditiq-footer__copy">© 2024 CreditIQ AI. All rights reserved.</div>
        </div>
      </footer>
    </div>
  );
}

export default Home;
