import React from 'react';
import { motion } from 'framer-motion';

interface ChartItem {
    label: string;
    value: number;
    color: string;
}

interface ChartSectionProps {
    title: string;
    subtitle?: string;
    data: ChartItem[];
    type?: 'bar' | 'line';
}

const ChartSection: React.FC<ChartSectionProps> = ({ title, subtitle, data, type = 'bar' }) => {
    const maxValue = Math.max(...data.map(d => d.value));

    return (
        <motion.div 
            className="creditiq-chart-card"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
            <div className="chart-header">
                <div className="header-text">
                    <h3>{title}</h3>
                    {subtitle && <p>{subtitle}</p>}
                </div>
            </div>

            <div className="chart-body">
                {type === 'bar' && (
                    <div className="bar-chart-container">
                        {data.map((item, index) => (
                            <div key={index} className="bar-item">
                                <div className="bar-info">
                                    <span className="bar-label">{item.label}</span>
                                    <span className="bar-value">{item.value}</span>
                                </div>
                                <div className="bar-wrapper">
                                    <motion.div 
                                        className="bar-fill"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${(item.value / maxValue) * 100}%` }}
                                        transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
                                        style={{ backgroundColor: item.color }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export default ChartSection;
