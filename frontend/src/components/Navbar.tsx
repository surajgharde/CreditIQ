import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Menu, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
  { id: 'product',         label: 'Product'  },
  { id: 'features',        label: 'Features' },
  { id: 'research',        label: 'Research' },
  { id: 'pricing',         label: 'Pricing'  },
  { id: 'history-section', label: 'History'  },
];

interface NavbarProps {
  activeSection: string;
  onScrollTo: (id: string) => void;
}

export default function Navbar({ activeSection, onScrollTo }: NavbarProps) {
  const { user, logout } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const handleNav = (id: string) => {
    onScrollTo(id);
    setMobileOpen(false);
  };

  return (
    <>
      <motion.nav
        className={`creditiq-navbar${scrolled ? ' creditiq-navbar--scrolled' : ''}`}
        initial={{ y: -80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="creditiq-navbar__inner">
          {/* Logo */}
          <Link to="/" className="creditiq-logo">
            <motion.div
              className="creditiq-logo__icon"
              whileHover={{ rotate: 15, scale: 1.1 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              <Zap size={18} fill="currentColor" stroke="none" />
            </motion.div>
            <span className="creditiq-logo__text">CreditIQ</span>
          </Link>

          {/* Desktop Nav Links */}
          <div className="creditiq-navbar__links">
            {NAV_ITEMS.map(({ id, label }) => (
              <motion.button
                key={id}
                className={`creditiq-nav-btn${activeSection === id ? ' creditiq-nav-btn--active' : ''}`}
                onClick={() => handleNav(id)}
                whileHover={{ y: -1 }}
                whileTap={{ scale: 0.96 }}
              >
                {label}
                {activeSection === id && (
                  <motion.span
                    className="creditiq-nav-btn__underline"
                    layoutId="nav-underline"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}
              </motion.button>
            ))}
          </div>

          {/* Right CTA */}
          <div className="creditiq-navbar__right">
            {user ? (
              <>
                <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                  <Link to="/newanalysis" className="creditiq-btn creditiq-btn--primary">
                    Start Analysis
                  </Link>
                </motion.div>
                <motion.button
                  onClick={logout}
                  className="creditiq-btn creditiq-btn--ghost"
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.97 }}
                >
                  Logout
                </motion.button>
              </>
            ) : (
              <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                <Link to="/login" className="creditiq-btn creditiq-btn--primary">Login</Link>
              </motion.div>
            )}

            {/* Mobile hamburger */}
            <button
              className="creditiq-hamburger"
              onClick={() => setMobileOpen(v => !v)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
      </motion.nav>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="creditiq-mobile-menu"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {NAV_ITEMS.map(({ id, label }) => (
              <button
                key={id}
                className={`creditiq-mobile-nav-btn${activeSection === id ? ' active' : ''}`}
                onClick={() => handleNav(id)}
              >
                {label}
              </button>
            ))}
            <div className="creditiq-mobile-menu__divider" />
            {user ? (
              <>
                <Link to="/newanalysis" className="creditiq-btn creditiq-btn--primary" onClick={() => setMobileOpen(false)}>
                  Start Analysis
                </Link>
                <button onClick={() => { logout(); setMobileOpen(false); }} className="creditiq-btn creditiq-btn--ghost">
                  Logout
                </button>
              </>
            ) : (
              <Link to="/login" className="creditiq-btn creditiq-btn--primary" onClick={() => setMobileOpen(false)}>
                Login
              </Link>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
