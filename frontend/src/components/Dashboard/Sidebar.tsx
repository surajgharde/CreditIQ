import React from 'react';
import { motion } from 'framer-motion';
import { LogOut, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';

interface SidebarItem {
    id: string;
    label: string;
    icon: any;
}

interface SidebarProps {
    items: SidebarItem[];
    activeTab: string;
    setActiveTab: (id: string) => void;
    logout: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ items, activeTab, setActiveTab, logout }) => {
    return (
        <aside className="creditiq-sidebar">
            <div className="sidebar-header">
                <Link to="/" className="sidebar-logo">
                    <div className="logo-icon">
                        <Zap size={20} fill="#fff" />
                    </div>
                    <span>CreditIQ AI</span>
                </Link>
            </div>
            
            <nav className="sidebar-nav">
                {items.map((item) => (
                    <button 
                        key={item.id}
                        className={`nav-btn ${activeTab === item.id ? 'active' : ''}`}
                        onClick={() => setActiveTab(item.id)}
                    >
                        <item.icon size={20} />
                        <span>{item.label}</span>
                        {activeTab === item.id && (
                            <motion.div 
                                className="active-indicator"
                                layoutId="sidebar-active"
                                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                            />
                        )}
                    </button>
                ))}
            </nav>

            <div className="sidebar-footer">
                <button onClick={logout} className="sidebar-logout">
                    <LogOut size={20} />
                    <span>Logout</span>
                </button>
            </div>
        </aside>
    );
};

export default Sidebar;
