// owner: Chetan (T3) — about page
import { motion, useReducedMotion } from 'framer-motion';
import {
  Shield,
  GraduationCap,
  Users,
  Server,
  Database,
  Lock,
  Network,
  ExternalLink,
  BookOpen,
  Cpu,
  Radio,
  Workflow,
  CheckCircle2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

// GitHub icon SVG component
function GithubIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg
      className={className}
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

// Track and Team Data according to PROJECT-ROADMAP.md §2
interface TeamMember {
  name: string;
  role: string;
  details: string;
  github?: string;
  handle?: string;
}

interface TrackGroup {
  trackId: string;
  trackName: string;
  leadNote?: string;
  members: TeamMember[];
}

const TRACKS: TrackGroup[] = [
  {
    trackId: 'T1',
    trackName: 'Core Crypto & DTE',
    leadNote: 'Lead + Integration Track',
    members: [
      {
        name: 'Nidhi',
        role: 'Track 1 Lead · DTE & PCFG',
        details:
          'PCFG model training on RockYou corpus, distribution-transforming encoders (Password & Username DTE), seed layouts, and total decoding guarantees.',
        github: 'https://github.com/Nidzz07',
        handle: '@Nidzz07',
      },
      {
        name: 'Dhruv',
        role: 'Crypto Engineer',
        details:
          'Argon2id KDF parameter profiling, unauthenticated AES-256-CTR stream cipher, Vault Blob v1 format, 3-emoji Vault Sigil, and attack/eval simulators.',
        github: 'https://github.com/dhruvgangurde',
        handle: '@dhruvgangurde',
      },
    ],
  },
  {
    trackId: 'T2',
    trackName: 'Backend API & Honeywords',
    members: [
      {
        name: 'Tanuj',
        role: 'API Core Engineer',
        details:
          'FastAPI application structure, JWT bearer security claims, slowapi rate limiting, SQLAlchemy 2.0 async models, and core vault entry endpoints.',
        github: 'https://github.com/tanujb03',
        handle: '@tanujb03',
      },
      {
        name: 'Rohan',
        role: 'Auth & Honeychecker · Repo Admin',
        details:
          'Dual-password registration/login auth flow, Juels-Rivest honeywords generation, honeychecker microservice, breach alerts, and share records.',
        github: 'https://github.com/rohansd05',
        handle: '@rohansd05',
      },
    ],
  },
  {
    trackId: 'T3',
    trackName: 'Frontend Experience',
    members: [
      {
        name: 'Krrish',
        role: 'Frontend Architect',
        details:
          'App shell foundation, client-side cryptographic state handling (zero master password storage in localStorage), auth flows, and vault dashboard.',
        github: 'https://github.com/krrishgadekar',
        handle: '@krrishgadekar',
      },
      {
        name: 'Chetan',
        role: 'UI & Lab Engineer',
        details:
          'Interactive Landing page with framer-motion demo, offline Attack Lab brute-force console, statistical Evaluation UI, Admin views, and About architecture.',
        github: 'https://github.com/ChetanC09',
        handle: '@ChetanC09',
      },
    ],
  },
  {
    trackId: 'T4',
    trackName: 'Security Infra & Deployment',
    members: [
      {
        name: 'Parth',
        role: 'PKI & Transport Engineer',
        details:
          '2-tier X.509 Certificate Authority, ECDH (P-256) credential sharing protocol, ECDSA digital signatures, and mTLS / signed inter-service transport.',
        github: 'https://github.com/Pgogg',
        handle: '@Pgogg',
      },
      {
        name: 'Vedant',
        role: 'DevOps & Deployment Owner',
        details:
          'Multi-stage Dockerfiles, Docker Compose service stack, GitHub Actions CI/CD workflows, and production deployments on Render, Neon, and Vercel.',
        github: 'https://github.com/vedantghuge22-hash',
        handle: '@vedantghuge22-hash',
      },
    ],
  },
  {
    trackId: 'T5',
    trackName: 'Utilities & Tooling',
    members: [
      {
        name: 'Tanmay',
        role: 'Corpus & Attack Tooling',
        details:
          'Attack dictionary generation from RockYou corpus, frequency-ranked Zipf distributions, and wordlist builder scripts for the evaluation harness.',
      },
      {
        name: 'Aryan',
        role: 'Strength & Entropy Utilities',
        details:
          'Password strength evaluation utilities, Shannon entropy calculations, pattern estimators, and model probability scoring helpers.',
      },
    ],
  },
];

// Academic References from PROJECT-BRIEF.md §17
interface ReferenceItem {
  id: number;
  authors: string;
  title: string;
  venue: string;
  year: string;
  notes: string;
}

const REFERENCES: ReferenceItem[] = [
  {
    id: 1,
    authors: 'Ari Juels and Thomas Ristenpart',
    title: 'Honey Encryption: Security Beyond the Brute-Force Bound',
    venue: 'EUROCRYPT 2014 (IACR Cryptology ePrint Archive 2014/155)',
    year: '2014',
    notes:
      'Foundational paper formalizing Distribution-Transforming Encoders (DTE) and message-recovery (MR) security bounds against offline brute-force attacks.',
  },
  {
    id: 2,
    authors: 'Rahul Chatterjee, Joseph Bonneau, Ari Juels, and Thomas Ristenpart',
    title: 'Cracking-Resistant Password Vaults using Natural Language Encoders',
    venue: 'IEEE Symposium on Security and Privacy (S&P 2015)',
    year: '2015',
    notes:
      'Introduced NoCrack: PCFG and n-gram natural-language encoders for structured password vaults, establishing statistical decoy generation principles.',
  },
  {
    id: 3,
    authors: 'Ari Juels and Ronald L. Rivest',
    title: 'Honeywords: Making Password-Cracking Detectable',
    venue: 'ACM Conference on Computer and Communications Security (CCS 2013)',
    year: '2013',
    notes:
      'Introduced sweetwords and the honeychecker architecture, turning stolen hashed password databases into active breach-detection tripwires.',
  },
  {
    id: 4,
    authors: 'Xavier Boyen, Joseph Bonneau, and Dan Boneh',
    title: 'Kamouflage: Loss-Resistant Biometric Authentication and Decoy Vaults',
    venue: 'Cryptographic security analysis in IEEE S&P',
    year: '2015',
    notes:
      'Exploration of decoy structures in biometric and password storage systems, inspiring our evaluation methodology against machine learning classifiers.',
  },
  {
    id: 5,
    authors: 'LastPass Security Incident Response',
    title: 'Notice of Recent Security Incident & Vault Exfiltration Analysis',
    venue: 'Public Security Incident Disclosure & Technical Post-Mortem',
    year: '2022',
    notes:
      'Documented the exfiltration of encrypted customer vault backups affecting 25M+ users, illustrating the real-world danger of conventional offline verification oracles.',
  },
  {
    id: 6,
    authors: 'Brian Krebs',
    title: 'LastPass: "Horse Gone Barn Bolted" Is Strong Password',
    venue: 'Krebs on Security Investigative Report',
    year: '2023',
    notes:
      'Investigation tracking over $35M in cryptocurrency theft resulting from offline cracking of stolen LastPass password vault backups.',
  },
  {
    id: 7,
    authors: 'William Stallings',
    title: 'Cryptography and Network Security: Principles and Practice (8th Edition)',
    venue: 'Pearson Education',
    year: '2020',
    notes:
      'Textbook covering modern stream cipher theory, elliptic-curve cryptography (ECDH/ECDSA), and public-key infrastructure (X.509).',
  },
  {
    id: 8,
    authors: 'IETF & Open-Source Security Implementations',
    title: 'RFC 9106 (Argon2), pyca/cryptography & Hypothesis Property-Based Testing',
    venue: 'Internet Engineering Task Force & Python Cryptographic Authority',
    year: '2021–2026',
    notes:
      'Specifications and tools utilized in HoneyVault: Argon2id memory-hard derivation, NIST P-256 curve mathematics, and formal property tests.',
  },
];

export function AboutPage() {
  const shouldReduceMotion = useReducedMotion();

  const fadeIn = {
    initial: { opacity: 0, y: shouldReduceMotion ? 0 : 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.5 },
  };

  return (
    <div className="relative min-h-screen bg-bg text-text-primary py-12 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto">
      {/* ── 1. HEADER & COURSE DETAILS ────────────────────────────── */}
      <motion.div {...fadeIn} className="text-center max-w-3xl mx-auto mb-16">
        <Badge variant="outline" className="mb-3 border-accent/40 text-accent bg-accent/5">
          <GraduationCap className="w-3.5 h-3.5 mr-1.5" /> ACNS-DC 2026-27 · SPIT Mumbai
        </Badge>
        <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text-primary mb-4">
          About <span className="text-gradient-honey">HoneyVault</span>
        </h1>
        <p className="text-text-secondary text-base sm:text-lg leading-relaxed">
          An advanced academic implementation of Honey Encryption, Honeywords breach detection,
          elliptic-curve credential sharing, and X.509 PKI, developed by <strong>Team Ocean's 10</strong>.
        </p>
      </motion.div>

      {/* Course Details Card */}
      <motion.div {...fadeIn} className="mb-16">
        <Card className="border-border bg-bg-surface/80 backdrop-blur-md">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2 text-accent">
              <GraduationCap className="w-5 h-5" />
              <CardTitle className="text-lg font-bold">Academic Context & Course Mapping</CardTitle>
            </div>
            <CardDescription className="text-xs sm:text-sm text-text-secondary">
              Applied Cryptography & Network Security Design Challenge (ACNS-DC 2026-27)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs sm:text-sm">
              <div className="p-3 rounded-lg bg-bg-elevated border border-border-subtle">
                <span className="text-text-muted text-[11px] uppercase block font-semibold">Course</span>
                <span className="font-semibold text-text-primary">CE305 / CS305 (CNS)</span>
              </div>
              <div className="p-3 rounded-lg bg-bg-elevated border border-border-subtle">
                <span className="text-text-muted text-[11px] uppercase block font-semibold">Institution</span>
                <span className="font-semibold text-text-primary">Sardar Patel Institute of Tech (SPIT)</span>
              </div>
              <div className="p-3 rounded-lg bg-bg-elevated border border-border-subtle">
                <span className="text-text-muted text-[11px] uppercase block font-semibold">Designation</span>
                <span className="font-semibold text-text-primary">ACNS Design Challenge</span>
              </div>
              <div className="p-3 rounded-lg bg-bg-elevated border border-border-subtle">
                <span className="text-text-muted text-[11px] uppercase block font-semibold">Team</span>
                <span className="font-semibold text-accent">Ocean's 10 (10 Members)</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* ── 2. STYLED COMPONENTS ARCHITECTURE DIAGRAM ─────────────── */}
      <motion.section {...fadeIn} className="mb-20">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <Badge variant="outline" className="mb-2 border-accent/40 text-accent bg-accent/5">
            <Workflow className="w-3.5 h-3.5 mr-1.5" /> System Architecture
          </Badge>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary mb-2">
            Multi-Tier Cryptographic Architecture
          </h2>
          <p className="text-xs sm:text-sm text-text-secondary">
            Built with styled React components illustrating service boundaries, transport encryption, and
            the isolated honeychecker security perimeter.
          </p>
        </div>

        {/* The Visual Architecture Container */}
        <div className="rounded-2xl border border-border bg-bg-surface/90 p-5 sm:p-8 shadow-elevated">
          {/* Top Level: Client Tier */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-mono font-bold uppercase text-accent tracking-wider">
                [Client Layer]
              </span>
              <span className="text-xs text-text-muted">Edge Browser Client</span>
            </div>
            <div className="p-4 sm:p-5 rounded-xl border border-accent/40 bg-bg-elevated flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-accent">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-text-primary">React Single Page App (SPA)</h3>
                  <p className="text-xs text-text-secondary">
                    Vite · React 18 · TypeScript · Tailwind CSS · Framer Motion · TanStack Query
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <Badge variant="secondary" className="font-mono">
                  Hosted on Vercel
                </Badge>
                <Badge variant="outline" className="text-accent border-accent/30">
                  Zero Master PW Storage
                </Badge>
              </div>
            </div>
          </div>

          {/* Connector 1: HTTPS + JWT */}
          <div className="flex flex-col items-center justify-center my-3 text-center">
            <div className="w-0.5 h-6 bg-border" />
            <div className="px-3 py-1 rounded-full bg-bg-elevated border border-border text-[11px] font-mono text-accent flex items-center gap-1.5 shadow-sm">
              <Lock className="w-3 h-3" />
              <span>HTTPS Transport + Bearer JWT Authentication</span>
            </div>
            <div className="w-0.5 h-6 bg-border" />
          </div>

          {/* Middle Level: Main Application & Pure Crypto Core */}
          <div className="mb-6 grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Main API Server */}
            <div className="lg:col-span-7 p-5 rounded-xl border border-border bg-bg-elevated flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono font-bold uppercase text-text-primary flex items-center gap-1.5">
                    <Server className="w-4 h-4 text-accent" />
                    honeyvault-api (FastAPI Core)
                  </span>
                  <Badge variant="secondary" className="text-[10px] font-mono">
                    Render Web Service
                  </Badge>
                </div>
                <p className="text-xs text-text-secondary mb-4">
                  Asynchronous REST API orchestrating user authentication, rate limiting, vault management,
                  evaluation APIs, and credential sharing envelopes.
                </p>
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-text-muted">
                  <div className="p-2 rounded bg-bg/80 border border-border-subtle">
                    /api/auth (Login/Register)
                  </div>
                  <div className="p-2 rounded bg-bg/80 border border-border-subtle">
                    /api/vault (Unlock/CRUD)
                  </div>
                  <div className="p-2 rounded bg-bg/80 border border-border-subtle">
                    /api/shares (ECDH E2E)
                  </div>
                  <div className="p-2 rounded bg-bg/80 border border-border-subtle">
                    /api/attack & /api/eval
                  </div>
                </div>
              </div>
            </div>

            {/* Pure Library: Honeycore */}
            <div className="lg:col-span-5 p-5 rounded-xl border border-accent/40 bg-accent/5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono font-bold uppercase text-accent flex items-center gap-1.5">
                    <Cpu className="w-4 h-4 text-accent" />
                    honeycore (Pure Python Library)
                  </span>
                  <Badge variant="outline" className="text-[10px] text-accent border-accent/30 font-mono">
                    Zero I/O Core
                  </Badge>
                </div>
                <p className="text-xs text-text-secondary mb-3">
                  Pure cryptographic primitives without database or network dependencies. Adheres strictly
                  to the frozen <code className="text-accent">interfaces.py</code> contract.
                </p>
                <ul className="space-y-1.5 text-xs text-text-secondary">
                  <li className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-accent" />
                    <span>DTE PCFG RockYou Password & Username Model</span>
                  </li>
                  <li className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-accent" />
                    <span>Argon2id KDF + AES-256-CTR (No MAC)</span>
                  </li>
                  <li className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-accent" />
                    <span>ECDH (P-256) + ECDSA + 2-Tier X.509 PKI</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Lower Level: Storage & Honeychecker Microservice */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Primary Postgres DB */}
            <div className="lg:col-span-5 p-4 rounded-xl border border-border bg-bg-elevated">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-bold uppercase text-text-primary flex items-center gap-1.5">
                  <Database className="w-4 h-4 text-info" />
                  Primary Neon Postgres DB
                </span>
                <Badge variant="secondary" className="text-[10px] font-mono">
                  Cloud Postgres
                </Badge>
              </div>
              <p className="text-xs text-text-secondary mb-2">
                Stores users, hashed sweetwords, vault ciphertext blobs, encrypted share envelopes, and
                breach alert logs.
              </p>
              <div className="text-[11px] font-mono text-text-muted space-y-1">
                <p>• users (login pw hash, sweetword list)</p>
                <p>• vaults (ciphertext, salt, nonce, v=1)</p>
                <p>• shares (ECDH sealed envelopes)</p>
              </div>
            </div>

            {/* Inter-Service Security Channel */}
            <div className="lg:col-span-2 flex flex-col items-center justify-center p-3 rounded-xl border border-border bg-bg text-center">
              <Network className="w-5 h-5 text-accent mb-1" />
              <span className="text-[10px] font-mono uppercase font-bold text-accent">
                Security Channel
              </span>
              <span className="text-[9px] text-text-muted mt-1 leading-tight">
                mTLS (Local) / Signed ECDSA Headers (Prod)
              </span>
              <span className="text-[9px] text-text-muted mt-1 font-mono">X.509 Verified</span>
            </div>

            {/* Honeychecker Service & DB */}
            <div className="lg:col-span-5 p-4 rounded-xl border border-warning/40 bg-warning/5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-bold uppercase text-warning flex items-center gap-1.5">
                  <Radio className="w-4 h-4 text-warning" />
                  honeychecker Microservice
                </span>
                <Badge variant="outline" className="text-[10px] text-warning border-warning/30 font-mono">
                  Isolated Service
                </Badge>
              </div>
              <p className="text-xs text-text-secondary mb-2">
                Completely isolated microservice with its own private database. Knows <strong>only</strong>{' '}
                the real sweetword index per user ID.
              </p>
              <div className="text-[11px] font-mono text-text-muted space-y-1 bg-bg/80 p-2 rounded border border-warning/20">
                <p className="text-warning font-semibold">• Private Neon DB: user_id → real_index</p>
                <p>• Decoy used → triggers instant breach alarm!</p>
              </div>
            </div>
          </div>
        </div>
      </motion.section>

      {/* ── 3. TEAM MEMBERS GROUPED BY TRACK ──────────────────────── */}
      <motion.section {...fadeIn} className="mb-20">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <Badge variant="outline" className="mb-2 border-accent/40 text-accent bg-accent/5">
            <Users className="w-3.5 h-3.5 mr-1.5" /> Team Ocean's 10
          </Badge>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary mb-2">
            Engineering Team by Track
          </h2>
          <p className="text-xs sm:text-sm text-text-secondary">
            Structured into 5 specialized tracks with clear cryptographic contracts and ownership boundaries.
          </p>
        </div>

        <div className="space-y-10">
          {TRACKS.map((track) => (
            <div key={track.trackId} className="space-y-4">
              <div className="flex items-center gap-3 pb-2 border-b border-border">
                <span className="text-xs font-mono font-bold px-2 py-1 rounded bg-accent/10 border border-accent/20 text-accent">
                  {track.trackId}
                </span>
                <h3 className="text-lg font-bold text-text-primary">{track.trackName}</h3>
                {track.leadNote && (
                  <Badge variant="secondary" className="text-[10px] text-text-secondary">
                    {track.leadNote}
                  </Badge>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {track.members.map((member) => (
                  <div
                    key={member.name}
                    className="p-5 rounded-xl border border-border bg-bg-surface hover:border-accent/30 transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div>
                          <h4 className="text-base font-bold text-text-primary">{member.name}</h4>
                          <p className="text-xs font-semibold text-accent">{member.role}</p>
                        </div>
                        {member.github && (
                          <a
                            href={member.github}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs font-mono text-text-muted hover:text-accent transition-colors px-2 py-1 rounded bg-bg-elevated border border-border-subtle"
                          >
                            <GithubIcon className="w-3.5 h-3.5" />
                            <span>{member.handle}</span>
                            <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                          </a>
                        )}
                      </div>
                      <p className="text-xs text-text-secondary leading-relaxed mt-2">{member.details}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </motion.section>

      {/* ── 4. ACADEMIC REFERENCES SECTION ────────────────────────── */}
      <motion.section {...fadeIn} className="mb-20">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <Badge variant="outline" className="mb-2 border-accent/40 text-accent bg-accent/5">
            <BookOpen className="w-3.5 h-3.5 mr-1.5" /> Academic Foundations
          </Badge>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary mb-2">
            Scientific Literature & References
          </h2>
          <p className="text-xs sm:text-sm text-text-secondary">
            Primary papers and standards cited in the project design brief (§17).
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {REFERENCES.map((ref) => (
            <div
              key={ref.id}
              className="p-5 rounded-xl border border-border bg-bg-surface/80 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono font-bold text-accent">[{ref.id}]</span>
                  <span className="text-[11px] font-mono text-text-muted">{ref.year}</span>
                </div>
                <h4 className="text-sm font-bold text-text-primary mb-1 leading-snug">{ref.title}</h4>
                <p className="text-xs text-text-secondary font-medium mb-2">{ref.authors}</p>
                <p className="text-xs text-text-muted italic mb-3">{ref.venue}</p>
              </div>
              <p className="text-xs text-text-secondary border-t border-border-subtle pt-2 leading-relaxed">
                {ref.notes}
              </p>
            </div>
          ))}
        </div>
      </motion.section>

      {/* ── 5. PROJECT DETAILS FOOTER NOTE ────────────────────────── */}
      <motion.div
        {...fadeIn}
        className="rounded-xl border border-border bg-bg-surface p-6 text-center text-xs text-text-muted space-y-2"
      >
        <p className="font-semibold text-text-secondary">
          HoneyVault — Team Ocean's 10 · SPIT Mumbai ACNS-DC 2026-27
        </p>
        <p>
          Submitted in partial fulfillment of the requirements for Cryptography & Network Security
          (CE305/CS305). Released under the MIT License for academic and research evaluation.
        </p>
      </motion.div>
    </div>
  );
}
