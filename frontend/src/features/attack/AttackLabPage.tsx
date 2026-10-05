// owner: Chetan (T3) — attack lab page (full impl in C1.1)
import { motion } from 'framer-motion';
import { FlaskConical, Zap, Lock } from 'lucide-react';

export function AttackLabPage() {
  return (
    <div style={{ padding: '4rem 1.5rem', maxWidth: 1200, margin: '0 auto' }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <div style={{ marginBottom: '3rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <div style={{
              width: 48, height: 48, borderRadius: 'var(--radius-lg)',
              background: 'rgba(245,165,36,0.1)', border: '1px solid rgba(245,165,36,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <FlaskConical size={24} style={{ color: 'var(--accent)' }} />
            </div>
            <div>
              <h1 style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                Attack Lab
              </h1>
              <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: '0.875rem' }}>
                {/* owner: Chetan */} Full implementation in C1 — Phase 1
              </p>
            </div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', lineHeight: 1.7, maxWidth: 600 }}>
            An interactive demonstration of offline dictionary attacks on conventional vs. honey-encrypted
            vaults. The attacker sees no difference between a correct and a decoy vault decryption.
          </p>
        </div>

        {/* Feature cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
          {[
            {
              icon: <Zap size={20} style={{ color: 'var(--accent)' }} />,
              title: 'Dictionary Attack',
              desc: 'Run up to 2000 guesses against both a conventional and a honey-encrypted vault simultaneously.',
            },
            {
              icon: <Lock size={20} style={{ color: 'var(--success)' }} />,
              title: 'Honeyword Detection',
              desc: 'See the live alarm when an attacker submits a stolen sweetword at the authentication gate.',
            },
            {
              icon: <FlaskConical size={20} style={{ color: 'var(--info)' }} />,
              title: 'Side-by-Side Comparison',
              desc: 'Compare attacker confusion across 500 distinct vault decryptions — every guess looks valid.',
            },
          ].map((card) => (
            <div
              key={card.title}
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '1.5rem',
              }}
            >
              <div style={{ marginBottom: '0.75rem' }}>{card.icon}</div>
              <h3 style={{ fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                {card.title}
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.6 }}>
                {card.desc}
              </p>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
