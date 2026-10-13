// owner: Krrish (T3) — 404 not found page
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Home } from 'lucide-react';

export function NotFoundPage() {
  return (
    <div
      style={{
        minHeight: 'calc(100vh - 128px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        textAlign: 'center',
      }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
      >
        <div
          style={{
            fontSize: '6rem',
            fontWeight: 900,
            background: 'linear-gradient(135deg, rgba(245,165,36,0.3), rgba(245,165,36,0.05))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            lineHeight: 1,
            marginBottom: '1rem',
            fontFamily: 'var(--font-mono)',
          }}
        >
          404
        </div>
        <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>🍯</div>
        <h1
          style={{
            fontSize: '1.5rem',
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginBottom: '0.75rem',
          }}
        >
          Page not found
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', maxWidth: 360 }}>
          This page doesn't exist — or like a decoy vault, it exists but contains nothing real.
        </p>
        <Link
          to="/"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.625rem 1.5rem',
            borderRadius: 'var(--radius-lg)',
            background: 'var(--accent)',
            color: '#000',
            fontWeight: 700,
            fontSize: '0.875rem',
            textDecoration: 'none',
          }}
        >
          <Home size={16} />
          Back to Home
        </Link>
      </motion.div>
    </div>
  );
}
