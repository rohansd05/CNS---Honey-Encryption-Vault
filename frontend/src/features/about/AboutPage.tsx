// owner: Chetan (T3) — about page (full impl in C1.4)
export function AboutPage() {
  const team = [
    { name: 'Nidhi', track: 'T1 — Crypto/DTE', role: 'Lead' },
    { name: 'Dhruv', track: 'T1 — Crypto/DTE', role: 'AES-CTR + KDF' },
    { name: 'Tanuj', track: 'T2 — API', role: 'Core models + Vault API' },
    { name: 'Rohan', track: 'T2 — API', role: 'Honeychecker + Auth' },
    { name: 'Krrish', track: 'T3 — Frontend', role: 'Scaffold + API client + Auth pages' },
    { name: 'Chetan', track: 'T3 — Frontend', role: 'Attack Lab + Admin + Evaluation UI' },
    { name: 'Parth', track: 'T4 — PKI/Sharing', role: 'PKI + Share flow' },
    { name: 'Vedant', track: 'T4 — DevOps', role: 'CI/CD + Docker' },
    { name: 'Tanmay', track: 'T5 — Strength/Corpus', role: 'Wordlist + entropy' },
    { name: 'Aryan', track: 'T5 — Strength/Corpus', role: 'Strength endpoint' },
  ];
  return (
    <div style={{ padding: '4rem 1.5rem', maxWidth: 900, margin: '0 auto' }}>
      {/* owner: Chetan — full about page in C1.4 */}
      <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
        About HoneyVault
      </h1>
      <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '3rem', maxWidth: 600 }}>
        A CNS course project implementing Honey Encryption for password vaults. Built by Team Ocean's 10
        at SPIT, 2026-27.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.75rem' }}>
        {team.map((m) => (
          <div
            key={m.name}
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%',
                background: 'linear-gradient(135deg, var(--accent), var(--accent-dim))',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 700, fontSize: '0.875rem', color: '#000',
              }}>
                {m.name[0]}
              </div>
              <div>
                <p style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9rem', margin: 0 }}>{m.name}</p>
                <p style={{ color: 'var(--accent)', fontSize: '0.7rem', margin: 0 }}>{m.track}</p>
              </div>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>{m.role}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
