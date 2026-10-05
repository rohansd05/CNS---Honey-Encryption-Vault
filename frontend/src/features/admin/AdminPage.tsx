// owner: Chetan (T3) — admin page (full impl in C1.3)
export function AdminPage() {
  return (
    <div style={{ padding: '4rem 1.5rem', maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '1rem', color: 'var(--text-primary)' }}>
        Admin Console
      </h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', lineHeight: 1.7 }}>
        {/* owner: Chetan */} Full implementation in C1 — honeyword alerts table, alert severity badges,
        source IP, sweetword index. Admin-only route.
      </p>
      <div style={{
        background: 'var(--bg-surface)', border: '1px dashed var(--border)',
        borderRadius: 'var(--radius-xl)', padding: '4rem', textAlign: 'center',
      }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🛡️</div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Admin dashboard — coming in Phase 1 (Chetan, C1.3)
        </p>
      </div>
    </div>
  );
}
