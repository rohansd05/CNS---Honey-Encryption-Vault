// owner: Chetan (T3) — landing page (placeholder; full impl in Phase 1/C1)
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, FlaskConical, ArrowRight } from 'lucide-react';

export function LandingPage() {
  return (
    <div
      style={{
        minHeight: 'calc(100vh - 64px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '4rem 1.5rem',
        textAlign: 'center',
      }}
    >
      {/* Background grid */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          background:
            'radial-gradient(ellipse 80% 60% at 50% -20%, rgba(245,165,36,0.08) 0%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        style={{ position: 'relative', zIndex: 1, maxWidth: 720 }}
      >
        {/* Badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.375rem 1rem',
            borderRadius: '9999px',
            border: '1px solid rgba(245,165,36,0.3)',
            background: 'rgba(245,165,36,0.08)',
            fontSize: '0.8rem',
            color: 'var(--accent)',
            fontWeight: 600,
            marginBottom: '2rem',
            letterSpacing: '0.04em',
          }}
        >
          <Shield size={13} />
          Honey Encryption Password Vault
        </div>

        <h1
          style={{
            fontSize: 'clamp(2.5rem, 6vw, 4.5rem)',
            fontWeight: 800,
            lineHeight: 1.05,
            letterSpacing: '-0.03em',
            color: 'var(--text-primary)',
            marginBottom: '1.5rem',
          }}
        >
          A stolen vault
          <br />
          <span
            style={{
              background: 'linear-gradient(135deg, #f5a524 0%, #f7c56a 50%, #f5a524 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            should be useless.
          </span>
        </h1>

        <p
          style={{
            fontSize: '1.125rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.7,
            marginBottom: '2.5rem',
            maxWidth: 560,
            margin: '0 auto 2.5rem',
          }}
        >
          Every wrong master password decrypts to a complete, plausible decoy vault — no MAC, no
          verification oracle. Built with PCFG Honey Encryption, Argon2id and AES-256-CTR.
        </p>

        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link
            to="/register"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.75rem 1.75rem',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--accent)',
              color: '#000',
              fontWeight: 700,
              fontSize: '0.95rem',
              textDecoration: 'none',
              boxShadow: '0 0 24px rgba(245,165,36,0.25)',
              transition: 'all 0.2s ease',
            }}
          >
            Get started <ArrowRight size={16} />
          </Link>
          <Link
            to="/attack"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.75rem 1.75rem',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border)',
              background: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              fontWeight: 600,
              fontSize: '0.95rem',
              textDecoration: 'none',
              transition: 'all 0.2s ease',
            }}
          >
            <FlaskConical size={16} style={{ color: 'var(--accent)' }} />
            Try the Attack Lab
          </Link>
        </div>
      </motion.div>

      <p
        style={{
          position: 'relative',
          zIndex: 1,
          marginTop: '3rem',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
        }}
      >
        {/* owner: Chetan — full landing page coming in C1 (Phase 1) */}
        Team Ocean's 10 · SPIT CNS ACNS-DC 2026-27
      </p>
    </div>
  );
}
