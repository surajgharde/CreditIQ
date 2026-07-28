import React from 'react';
import { motion } from 'framer-motion';

interface DashboardCardProps {
    title: string;
    value: string | number;
    delta?: string;
    icon: React.ReactNode;
    color?: string;
    bg?: string;
    delay?: number;
}

const DashboardCard: React.FC<DashboardCardProps> = ({ title, value, delta, icon, color, bg, delay = 0 }) => {
    return (
        <motion.div 
            className="creditiq-dash-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            whileHover={{ y: -5, boxShadow: '0 12px 24px rgba(0,0,0,0.1)' }}
        >
            <div className="card-icon-box" style={{ backgroundColor: bg, color: color }}>
                {icon}
            </div>
            <div className="card-info">
                <span className="card-label">{title}</span>
                <span className="card-value" style={{ color }}>{value}</span>
                {delta && <span className="card-delta">{delta}</span>}
            </div>
            <div className="card-accent-bar" style={{ backgroundColor: color }} />
        </motion.div>
    );
};

export default DashboardCard;
