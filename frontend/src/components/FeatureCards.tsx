import { motion } from 'framer-motion';
import {
  FileText, AlertTriangle, BarChart3, Newspaper, BookOpen, Shield
} from 'lucide-react';

const FEATURES = [
  {
    icon: <FileText size={22} />,
    title: 'Document AI (OCR)',
    desc: 'Extracts financial tables from scanned PDFs using PdfTable + AWS Textract with 97%+ accuracy.',
    color: '#14b8a6',
    bg: '#14b8a610',
  },
  {
    icon: <AlertTriangle size={22} />,
    title: 'Fraud Detection',
    desc: 'Detects GST mismatch, circular trading, and promoter defaults via real-time API cross-verification.',
    color: '#ef4444',
    bg: '#ef444412',
  },
  {
    icon: <BarChart3 size={22} />,
    title: 'Risk Scoring',
    desc: 'Calibrated XGBoost model trained on RBI NPA data computes PD with SHAP waterfall explanations.',
    color: '#10b981',
    bg: '#10b98112',
  },
  {
    icon: <Newspaper size={22} />,
    title: 'News Intelligence',
    desc: 'FinBERT scans 24+ news sources for negative signals — court cases, defaults, regulatory actions.',
    color: '#f59e0b',
    bg: '#f59e0b12',
  },
  {
    icon: <BookOpen size={22} />,
    title: 'CAM Writer',
    desc: 'Cohere Command-R generates a fully formatted Credit Appraisal Memo with dynamic conditions.',
    color: '#0891b2',
    bg: '#0891b212',
  },
  {
    icon: <Shield size={22} />,
    title: 'Early Warning System',
    desc: 'Real-time monitoring dashboard with threshold alerts and SMS/email triggers via Twilio + SendGrid.',
    color: '#0891b2',
    bg: '#0891b212',
  },
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.08 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] } },
};

export default function FeatureCards() {
  return (
    <section id="features" className="creditiq-section creditiq-section--alt">
      <div className="creditiq-container">
        <motion.div
          className="creditiq-section__header"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="creditiq-section__label">FEATURES</div>
          <h2 className="creditiq-section__title">Everything You Need for<br />Intelligent Credit Appraisal</h2>
          <p className="creditiq-section__subtitle">
            Six powerful AI engines working in concert to give you complete credit visibility.
          </p>
        </motion.div>

        <motion.div
          className="creditiq-features-grid"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-60px' }}
        >
          {FEATURES.map(({ icon, title, desc, color, bg }) => (
            <motion.div
              key={title}
              className="creditiq-feature-card"
              variants={cardVariants}
              whileHover={{ y: -6, boxShadow: `0 20px 40px ${color}22` }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            >
              <div
                className="creditiq-feature-card__icon"
                style={{ background: bg, color }}
              >
                {icon}
              </div>
              <h4 className="creditiq-feature-card__title">{title}</h4>
              <p className="creditiq-feature-card__desc">{desc}</p>
              <div className="creditiq-feature-card__accent" style={{ background: color }} />
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
