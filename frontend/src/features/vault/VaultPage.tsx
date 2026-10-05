// owner: Krrish (T3) — vault page placeholder (full impl in Phase 2 K2.1)
export function VaultPage() {
  return (
    <div style={{ minHeight: 'calc(100vh - 128px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-xl)', padding: '3rem', textAlign: 'center', maxWidth: 500, width: '100%',
      }}>
        <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>🔐</div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Your Vault</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
          Vault page — unlock screen with sigil, entries table, add/edit/delete dialogs
        </p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Owner: Krrish · Full impl Phase 2 K2.1</p>
      </div>
    </div>
  );
}
