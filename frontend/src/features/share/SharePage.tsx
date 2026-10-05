// owner: Krrish (T3) — share page placeholder (full impl in Phase 2 K2.2)
export function SharePage() {
  return (
    <div style={{ minHeight: 'calc(100vh - 128px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-xl)', padding: '3rem', textAlign: 'center', maxWidth: 500, width: '100%',
      }}>
        <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📬</div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Secure Share</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
          Share page — inbox, sent, open share flows with PKI signature validation
        </p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Owner: Krrish · Full impl Phase 2 K2.2</p>
      </div>
    </div>
  );
}
