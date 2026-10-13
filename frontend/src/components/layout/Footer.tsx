// owner: Krrish (T3) — footer
import { Link } from 'react-router-dom';
import { Shield, ExternalLink } from 'lucide-react';

function GithubIcon({ size = 14 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

export function Footer() {
  return (
    <footer
      style={{
        borderTop: '1px solid var(--border)',
        background: 'var(--bg-surface)',
        padding: '2rem 1.5rem',
        marginTop: 'auto',
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          margin: '0 auto',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '2rem',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <Shield size={18} style={{ color: 'var(--accent)' }} />
            <span
              style={{
                fontWeight: 700,
                background: 'linear-gradient(135deg, #f5a524, #f7c56a)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              HoneyVault
            </span>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: 280, lineHeight: 1.5 }}>
            A stolen vault should be useless. Every wrong master password returns a plausible decoy — no
            offline cracking oracle.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '3rem', flexWrap: 'wrap' }}>
          <FooterCol
            title="Project"
            links={[
              { label: 'Attack Lab', to: '/attack' },
              { label: 'Evaluation', to: '/evaluation' },
              { label: 'About', to: '/about' },
            ]}
          />
          <FooterCol
            title="Resources"
            links={[
              {
                label: 'GitHub',
                href: 'https://github.com/rohansd05/CNS---Honey-Encryption-Vault',
                external: true,
              },
              { label: 'API Docs', href: 'http://localhost:8000/docs', external: true },
            ]}
          />
        </div>
      </div>

      <div
        style={{
          maxWidth: 1200,
          margin: '1.5rem auto 0',
          paddingTop: '1rem',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.5rem',
        }}
      >
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          © 2026 Team Ocean's 10 · SPIT CNS ACNS-DC · MIT License
        </p>
        <a
          href="https://github.com/rohansd05/CNS---Honey-Encryption-Vault"
          target="_blank"
          rel="noreferrer"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.375rem',
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            textDecoration: 'none',
          }}
        >
          <GithubIcon size={14} />
          rohansd05/CNS---Honey-Encryption-Vault
        </a>
      </div>
    </footer>
  );
}

function FooterCol({
  title,
  links,
}: {
  title: string;
  links: Array<{ label: string; to?: string; href?: string; external?: boolean }>;
}) {
  return (
    <div>
      <p
        style={{
          fontSize: '0.75rem',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--text-muted)',
          marginBottom: '0.75rem',
        }}
      >
        {title}
      </p>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {links.map((link) => (
          <li key={link.label}>
            {link.to ? (
              <Link
                to={link.to}
                style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', textDecoration: 'none' }}
              >
                {link.label}
              </Link>
            ) : (
              <a
                href={link.href}
                target={link.external ? '_blank' : undefined}
                rel={link.external ? 'noreferrer' : undefined}
                style={{
                  fontSize: '0.875rem',
                  color: 'var(--text-secondary)',
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                {link.label}
                {link.external && <ExternalLink size={11} />}
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
