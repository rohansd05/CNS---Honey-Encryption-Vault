// owner: Krrish (T3) — top navigation bar
import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Menu,
  X,
  Sun,
  Moon,
  LogOut,
  User,
  ChevronDown,
  FlaskConical,
  BarChart3,
  Settings,
  Info,
  Share2,
  Vault,
} from 'lucide-react';
import { useTheme } from '@/lib/theme';
import { useAuth } from '@/lib/auth';

interface NavItem {
  label: string;
  to: string;
  icon: React.ReactNode;
  ownerNote?: string;
}

const navItems: NavItem[] = [
  { label: 'Vault', to: '/vault', icon: <Vault size={16} /> },
  { label: 'Share', to: '/share', icon: <Share2 size={16} /> },
  { label: 'Attack Lab', to: '/attack', icon: <FlaskConical size={16} />, ownerNote: 'Chetan' },
  { label: 'Evaluation', to: '/evaluation', icon: <BarChart3 size={16} />, ownerNote: 'Chetan' },
  { label: 'Admin', to: '/admin', icon: <Settings size={16} />, ownerNote: 'Chetan' },
  { label: 'About', to: '/about', icon: <Info size={16} />, ownerNote: 'Chetan' },
];

const activeLinkStyle: React.CSSProperties = {
  color: 'var(--accent)',
  borderBottom: '2px solid var(--accent)',
};

export function Navbar() {
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    setUserMenuOpen(false);
    navigate('/');
  };

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        borderBottom: '1px solid var(--border)',
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
      }}
    >
      <nav
        style={{
          maxWidth: 1200,
          margin: '0 auto',
          padding: '0 1.5rem',
          height: 64,
          display: 'flex',
          alignItems: 'center',
          gap: '2rem',
        }}
      >
        {/* Logo */}
        <Link
          to="/"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            textDecoration: 'none',
            flexShrink: 0,
          }}
        >
          <HoneycombLogo />
          <span
            style={{
              fontWeight: 700,
              fontSize: '1.125rem',
              letterSpacing: '-0.02em',
              background: 'linear-gradient(135deg, #f5a524, #f7c56a)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            HoneyVault
          </span>
        </Link>

        {/* Desktop nav links */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.125rem',
            flex: 1,
          }}
          className="hidden-mobile"
        >
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '0.375rem',
                padding: '0.375rem 0.75rem',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontWeight: 500,
                textDecoration: 'none',
                color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-glow)' : 'transparent',
                transition: 'all 0.15s ease',
              })}
              onMouseEnter={(e) => {
                if (!(e.currentTarget as HTMLElement).style.background.includes('accent-glow')) {
                  (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)';
                  (e.currentTarget as HTMLElement).style.background = 'var(--bg-elevated)';
                }
              }}
              onMouseLeave={(e) => {
                const active = window.location.pathname === item.to;
                (e.currentTarget as HTMLElement).style.color = active
                  ? 'var(--accent)'
                  : 'var(--text-secondary)';
                (e.currentTarget as HTMLElement).style.background = active
                  ? 'var(--accent-glow)'
                  : 'transparent';
              }}
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </div>

        {/* Right actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: 'auto' }}>
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle theme"
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border)',
              background: 'var(--bg-surface)',
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              flexShrink: 0,
            }}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {/* User menu or login */}
          {user ? (
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => {
                  setUserMenuOpen((v) => !v);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.375rem 0.75rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                }}
              >
                <div
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, var(--accent), var(--accent-dim))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    color: '#000',
                  }}
                >
                  {user.username[0].toUpperCase()}
                </div>
                <span className="hidden-mobile">{user.username}</span>
                <ChevronDown size={14} style={{ color: 'var(--text-muted)' }} />
              </button>

              <AnimatePresence>
                {userMenuOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -8, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -8, scale: 0.95 }}
                    transition={{ duration: 0.15 }}
                    style={{
                      position: 'absolute',
                      top: '100%',
                      right: 0,
                      marginTop: '0.5rem',
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-lg)',
                      padding: '0.5rem',
                      minWidth: 180,
                      boxShadow: 'var(--shadow-elevated)',
                      zIndex: 60,
                    }}
                  >
                    <div
                      style={{
                        padding: '0.5rem 0.75rem',
                        borderBottom: '1px solid var(--border)',
                        marginBottom: '0.25rem',
                      }}
                    >
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Signed in as</p>
                      <p
                        style={{
                          fontSize: '0.875rem',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {user.username}
                      </p>
                    </div>
                    <MenuBtn
                      icon={<User size={14} />}
                      label="Profile"
                      onClick={() => {
                        setUserMenuOpen(false);
                      }}
                    />
                    <MenuBtn
                      icon={<LogOut size={14} />}
                      label="Sign out"
                      onClick={handleLogout}
                      danger
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <Link
              to="/login"
              style={{
                padding: '0.375rem 1rem',
                borderRadius: 'var(--radius-md)',
                background: 'var(--accent)',
                color: '#000',
                fontWeight: 600,
                fontSize: '0.875rem',
                textDecoration: 'none',
                transition: 'all 0.15s ease',
              }}
            >
              Sign in
            </Link>
          )}

          {/* Mobile hamburger */}
          <button
            onClick={() => {
              setMenuOpen((v) => !v);
            }}
            aria-label="Toggle menu"
            className="show-mobile"
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border)',
              background: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              display: 'none',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
          >
            {menuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{
              overflow: 'hidden',
              borderTop: '1px solid var(--border)',
              background: 'var(--bg-surface)',
            }}
          >
            <div style={{ padding: '1rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => {
                    setMenuOpen(false);
                  }}
                  style={({ isActive }) => ({
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.625rem 0.75rem',
                    borderRadius: 'var(--radius-md)',
                    textDecoration: 'none',
                    color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                    background: isActive ? 'var(--accent-glow)' : 'transparent',
                    fontWeight: 500,
                    fontSize: '0.9rem',
                    ...(isActive ? activeLinkStyle : {}),
                  })}
                >
                  {item.icon}
                  {item.label}
                </NavLink>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        @media (max-width: 768px) {
          .hidden-mobile { display: none !important; }
          .show-mobile { display: flex !important; }
        }
      `}</style>
    </header>
  );
}

function HoneycombLogo() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <polygon
        points="16,2 26,8 26,20 16,26 6,20 6,8"
        fill="rgba(245,165,36,0.15)"
        stroke="#f5a524"
        strokeWidth="1.5"
      />
      <polygon
        points="16,7 21,10 21,16 16,19 11,16 11,10"
        fill="rgba(245,165,36,0.3)"
        stroke="#f5a524"
        strokeWidth="1"
      />
      <circle cx="16" cy="13" r="2" fill="#f5a524" />
    </svg>
  );
}

function MenuBtn({
  icon,
  label,
  onClick,
  danger,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.5rem 0.75rem',
        borderRadius: 'var(--radius-md)',
        border: 'none',
        background: 'transparent',
        color: danger ? 'var(--danger)' : 'var(--text-primary)',
        cursor: 'pointer',
        fontSize: '0.875rem',
        textAlign: 'left',
        transition: 'background 0.1s',
      }}
      onMouseEnter={(e) =>
        ((e.currentTarget as HTMLElement).style.background = danger
          ? 'var(--danger-bg)'
          : 'var(--bg-overlay)')
      }
      onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
    >
      {icon}
      {label}
    </button>
  );
}
