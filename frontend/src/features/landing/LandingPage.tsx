// owner: Chetan (T3) — landing page
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  ArrowRight,
  FlaskConical,
  Lock,
  Key,
  Cpu,
  Network,
  Share2,
  AlertTriangle,
  CheckCircle2,
  Copy,
  Check,
  Terminal,
  Layers,
  Sparkles,
  Fingerprint,
  Radio,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

// Realistic mock credentials for the animated demo
interface VaultEntry {
  service: string;
  username: string;
  password: string;
}

interface DemoVaultResult {
  isReal: boolean;
  tag: string;
  sigil: {
    emojis: [string, string, string];
    color: string;
  };
  entries: VaultEntry[];
  note: string;
}

const REAL_PASSWORD = 'CorrectMasterPass2026!';

const DEMO_PRESETS = [
  { id: 'real', label: 'Correct Key (User)', password: REAL_PASSWORD, isReal: true },
  { id: 'wrong1', label: 'Guess: "password123"', password: 'password123', isReal: false },
  { id: 'wrong2', label: 'Guess: "Winter2023!"', password: 'Winter2023!', isReal: false },
  { id: 'wrong3', label: 'Guess: "hunter2"', password: 'hunter2', isReal: false },
  { id: 'wrong4', label: 'Guess: "admin2026"', password: 'admin2026', isReal: false },
];

// Deterministic decoy generator for arbitrary inputs
function getDecoyForPassword(password: string): DemoVaultResult {
  if (password === REAL_PASSWORD) {
    return {
      isReal: true,
      tag: 'REAL VAULT · AUTHORIZED MASTER KEY',
      sigil: {
        emojis: ['🦁', '🗝️', '🌊'],
        color: '#f5a524',
      },
      entries: [
        { service: 'github.com', username: 'chetan_dev', password: 'ghp_K9d8vL7w9xM4pQ2a' },
        { service: 'proton.me', username: 'chetan.c@pm.me', password: 'S3cure!Ocean#2026' },
        { service: 'aws.amazon.com', username: 'root@honeyvault.io', password: 'K7#m9$Qv2!xP84La' },
        { service: 'bitwarden.com', username: 'vault_admin', password: 'Tr0ub4dor&3#SPIT' },
      ],
      note: 'Decryption succeeded with authentic master password. Sigil matches user visual memory.',
    };
  }

  // Generate plausible PCFG-style decoys deterministically from the input string
  let hash = 0;
  for (let i = 0; i < password.length; i++) {
    hash = (hash << 5) - hash + password.charCodeAt(i);
    hash |= 0;
  }
  const absHash = Math.abs(hash);

  const emojiSets: Array<[string, string, string]> = [
    ['🦊', '⚡', '🌲'],
    ['🦅', '🔮', '🌙'],
    ['🐻', '🔥', '🛡️'],
    ['🐺', '❄️', '⭐'],
    ['🐬', '🌊', '⚓'],
    ['🐯', '🌿', '🧭'],
  ];

  const colors = ['#38bdf8', '#a855f7', '#ec4899', '#10b981', '#f97316', '#06b6d4'];

  const decoyUsers = [
    'j_miller92',
    'alex_turner84',
    'sarah.crypto',
    'david_k99',
    'marcus.w',
    'elena.smith',
    'chris_p2022',
  ];

  const decoyPasswords = [
    'Blueberry#2019',
    'Winter2023!',
    'DragonFly#42',
    'SilverMoon$88',
    'CoffeeCup*2021',
    'SunsetBeach!99',
    'RedPanda!55',
  ];

  const setIndex = absHash % emojiSets.length;
  const colorIndex = (absHash >> 2) % colors.length;
  const uIndex = (absHash >> 3) % decoyUsers.length;
  const pIndex = (absHash >> 4) % decoyPasswords.length;

  return {
    isReal: false,
    tag: 'DECOY VAULT · OFFLINE ATTACK GUESS',
    sigil: {
      emojis: emojiSets[setIndex],
      color: colors[colorIndex],
    },
    entries: [
      {
        service: 'github.com',
        username: decoyUsers[uIndex],
        password: decoyPasswords[pIndex],
      },
      {
        service: 'proton.me',
        username: `${decoyUsers[(uIndex + 1) % decoyUsers.length]}@proton.me`,
        password: decoyPasswords[(pIndex + 1) % decoyPasswords.length],
      },
      {
        service: 'aws.amazon.com',
        username: `infra.${decoyUsers[(uIndex + 2) % decoyUsers.length]}@cloudops.net`,
        password: decoyPasswords[(pIndex + 2) % decoyPasswords.length],
      },
      {
        service: 'bitwarden.com',
        username: decoyUsers[(uIndex + 3) % decoyUsers.length],
        password: decoyPasswords[(pIndex + 3) % decoyPasswords.length],
      },
    ],
    note: 'Stream cipher XORed keystream + DTE PCFG decoded valid credentials without any error.',
  };
}

export function LandingPage() {
  const shouldReduceMotion = useReducedMotion();
  const [activePassword, setActivePassword] = useState(REAL_PASSWORD);
  const [customInput, setCustomInput] = useState('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const currentResult = getDecoyForPassword(activePassword);

  const handleCopy = (text: string, id: string) => {
    void navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => {
      setCopiedKey(null);
    }, 1500);
  };

  const handleCustomSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (customInput.trim()) {
      setActivePassword(customInput.trim());
    }
  };

  const transitionConfig = shouldReduceMotion
    ? { duration: 0 }
    : { duration: 0.4, ease: [0.16, 1, 0.3, 1] };

  return (
    <div className="relative min-h-screen bg-bg text-text-primary overflow-x-hidden">
      {/* Background radial atmosphere */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background:
            'radial-gradient(ellipse 90% 55% at 50% -10%, rgba(245,165,36,0.12) 0%, rgba(19,29,46,0.5) 60%, transparent 100%)',
        }}
      />
      <div
        className="fixed inset-0 pointer-events-none z-0 opacity-20"
        style={{
          backgroundImage:
            'linear-gradient(to right, rgba(36,53,82,0.3) 1px, transparent 1px), linear-gradient(to bottom, rgba(36,53,82,0.3) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      {/* ── 1. HERO SECTION ───────────────────────────────────────── */}
      <section className="relative z-10 pt-16 pb-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto text-center">
        {/* Course Badge */}
        <motion.div
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-accent/30 bg-accent/10 text-accent text-xs sm:text-sm font-semibold mb-8 shadow-sm backdrop-blur-sm"
        >
          <Shield className="w-4 h-4 text-accent" />
          <span>Honey Encryption Password Vault · ACNS-DC 2026-27 · SPIT</span>
        </motion.div>

        {/* Hero Title */}
        <motion.h1
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-text-primary leading-[1.08] mb-6"
        >
          A stolen vault <br className="hidden sm:inline" />
          <span className="text-gradient-honey">should be worthless.</span>
        </motion.h1>

        {/* Sub-line on Honey Encryption */}
        <motion.p
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-lg sm:text-xl text-text-secondary max-w-3xl mx-auto leading-relaxed mb-10"
        >
          Conventional vaults hand offline attackers a verification oracle: wrong master passwords fail
          with an error, confirming when a crack succeeds. HoneyVault applies <strong>Honey Encryption</strong>:
          every wrong master password decrypts to a statistically natural, realistic <strong>decoy vault</strong>.
          An offline attacker gets zero signal.
        </motion.p>

        {/* Primary CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-wrap items-center justify-center gap-4 mb-16"
        >
          <Button asChild size="lg" className="rounded-xl px-7 py-6 text-base shadow-glow">
            <Link to="/register" className="flex items-center gap-2">
              Create Honey Vault
              <ArrowRight className="w-4 h-4" />
            </Link>
          </Button>

          <Button
            asChild
            variant="outline"
            size="lg"
            className="rounded-xl px-7 py-6 text-base border-border hover:bg-bg-elevated text-text-primary"
          >
            <Link to="/attack" className="flex items-center gap-2">
              <FlaskConical className="w-4 h-4 text-accent" />
              Launch Attack Lab
            </Link>
          </Button>
        </motion.div>

        {/* Quick Highlights Strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 max-w-4xl mx-auto text-left"
        >
          {[
            { label: 'Ciphertext Verification', value: 'Zero Oracle', sub: 'No MAC or auth tag' },
            { label: 'Wrong Passwords', value: '100% Decoys', sub: 'Total DTE decoding' },
            { label: 'Brute-Force Signal', value: '0 Bits', sub: 'Identical timing & shape' },
            { label: 'Breach Detection', value: 'Honeywords', sub: 'Instant alarm on decoy' },
          ].map((item, idx) => (
            <div
              key={idx}
              className="p-3.5 sm:p-4 rounded-xl border border-border bg-bg-surface/80 backdrop-blur-sm"
            >
              <p className="text-[11px] uppercase tracking-wider text-text-muted font-medium mb-1">
                {item.label}
              </p>
              <p className="text-base sm:text-lg font-bold text-accent">{item.value}</p>
              <p className="text-xs text-text-secondary">{item.sub}</p>
            </div>
          ))}
        </motion.div>
      </section>

      {/* ── 2. ANIMATED HONEY ENCRYPTION DEMO ─────────────────────── */}
      <section className="relative z-10 py-16 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto">
        <div className="text-center mb-10">
          <Badge variant="outline" className="mb-3 border-accent/40 text-accent bg-accent/5">
            <Sparkles className="w-3 h-3 mr-1" /> Interactive Demonstration
          </Badge>
          <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-text-primary mb-3">
            One Ciphertext. Infinite Plausible Vaults.
          </h2>
          <p className="text-text-secondary text-sm sm:text-base max-w-2xl mx-auto">
            Test master passwords against the exact same stolen ciphertext blob. Watch how both the
            authentic key and attacker guesses unlock valid, structured vaults with{' '}
            <strong className="text-text-primary">no error and no signal</strong>.
          </p>
        </div>

        {/* Interactive Demo Card */}
        <div className="rounded-2xl border border-border bg-bg-surface shadow-elevated p-5 sm:p-8 backdrop-blur-md">
          {/* Stolen Ciphertext Banner */}
          <div className="mb-6 p-4 rounded-xl bg-bg-elevated border border-border">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-accent" />
                <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                  Exfiltrated Ciphertext Blob (Fixed 532 Bytes)
                </span>
              </div>
              <Badge variant="secondary" className="text-[11px] font-mono">
                AES-256-CTR · No MAC · No Padding
              </Badge>
            </div>
            <p className="text-xs font-mono text-text-muted break-all select-all bg-bg/80 p-2.5 rounded-lg border border-border-subtle leading-relaxed">
              9f8c2e4b71d0a35fe629b8014d7c83f120aa56bcde4938210f92b7405e61283c74a912e8b0f453a2cd7810
              49b6f3e1a024c8d571ef9302b4859a6c7104d82b3e7f910a2b... [532 bytes total]
            </p>
          </div>

          {/* Preset Buttons & Custom Input */}
          <div className="mb-6">
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2.5">
              Select or test a Master Password:
            </label>
            <div className="flex flex-wrap gap-2 mb-4">
              {DEMO_PRESETS.map((preset) => {
                const isActive = activePassword === preset.password;
                return (
                  <button
                    key={preset.id}
                    onClick={() => {
                      setActivePassword(preset.password);
                    }}
                    className={`text-xs px-3 py-2 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                      isActive
                        ? preset.isReal
                          ? 'bg-accent text-black font-semibold shadow-glow'
                          : 'bg-info/20 text-info border border-info/40'
                        : 'bg-bg-elevated border border-border text-text-secondary hover:text-text-primary hover:border-border/80'
                    }`}
                  >
                    {preset.isReal ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                      <AlertTriangle className="w-3.5 h-3.5 text-warning" />
                    )}
                    {preset.label}
                  </button>
                );
              })}
            </div>

            {/* Custom Input Form */}
            <form onSubmit={handleCustomSubmit} className="flex gap-2">
              <div className="relative flex-1">
                <Key className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  placeholder="Or type any arbitrary guess (e.g. 'Dragon2026!', 'qwerty', 'solar-storm')..."
                  value={customInput}
                  onChange={(e) => {
                    setCustomInput(e.target.value);
                  }}
                  className="w-full pl-9 pr-3 py-2 text-xs sm:text-sm bg-bg-elevated border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>
              <Button type="submit" variant="secondary" size="sm" className="px-4 text-xs font-semibold">
                Test Guess
              </Button>
            </form>
          </div>

          {/* Animated Vault Card Result */}
          <div className="relative">
            <AnimatePresence mode="wait">
              <motion.div
                key={activePassword}
                initial={{ opacity: 0, scale: shouldReduceMotion ? 1 : 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: shouldReduceMotion ? 1 : 0.98 }}
                transition={transitionConfig}
                className={`rounded-xl border p-5 sm:p-6 transition-all ${
                  currentResult.isReal
                    ? 'border-accent/50 bg-bg-elevated/90 shadow-glow'
                    : 'border-border bg-bg-elevated/70'
                }`}
              >
                {/* Vault Card Header */}
                <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-border/80 mb-5">
                  <div className="flex items-center gap-3">
                    {/* Sigil Preview */}
                    <div
                      className="flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg border border-border/60 font-mono text-base"
                      style={{
                        backgroundColor: `${currentResult.sigil.color}15`,
                        borderColor: currentResult.sigil.color,
                      }}
                      title="Vault Sigil: deterministic 3-emoji key fingerprint"
                    >
                      <span>{currentResult.sigil.emojis[0]}</span>
                      <span>{currentResult.sigil.emojis[1]}</span>
                      <span>{currentResult.sigil.emojis[2]}</span>
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm sm:text-base font-bold text-text-primary">
                          Decrypted Vault Instance
                        </span>
                        <Badge
                          variant={currentResult.isReal ? 'default' : 'secondary'}
                          className="text-[10px] uppercase font-bold"
                        >
                          {currentResult.isReal ? 'Authentic Vault' : 'Decoy Vault'}
                        </Badge>
                      </div>
                      <p className="text-xs text-text-muted">
                        Key input: <code className="text-text-secondary font-mono">"{activePassword}"</code>
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-bold bg-success/10 text-success border border-success/30">
                      HTTP 200 OK · 120ms
                    </span>
                    <p className="text-[11px] text-text-muted mt-0.5">Zero decryption exceptions</p>
                  </div>
                </div>

                {/* Decoded Entries Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
                  {currentResult.entries.map((entry, index) => (
                    <div
                      key={index}
                      className="p-3 rounded-lg bg-bg/70 border border-border-subtle flex flex-col justify-between"
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-semibold text-accent">{entry.service}</span>
                        <button
                          onClick={() => {
                            handleCopy(entry.password, `${entry.service}-${String(index)}`);
                          }}
                          className="text-text-muted hover:text-text-primary transition-colors p-1"
                          title="Copy password"
                        >
                          {copiedKey === `${entry.service}-${String(index)}` ? (
                            <Check className="w-3.5 h-3.5 text-success" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                      <div className="text-xs space-y-0.5">
                        <p className="text-text-secondary">
                          User: <span className="font-mono text-text-primary">{entry.username}</span>
                        </p>
                        <p className="text-text-secondary">
                          Pass: <span className="font-mono text-text-primary font-medium">{entry.password}</span>
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Oracle Callout Banner */}
                <div className="p-3 rounded-lg bg-bg border border-border/80 flex items-start gap-3">
                  <div className="mt-0.5">
                    {currentResult.isReal ? (
                      <ShieldCheck className="w-5 h-5 text-accent flex-shrink-0" />
                    ) : (
                      <Radio className="w-5 h-5 text-info flex-shrink-0" />
                    )}
                  </div>
                  <div className="text-xs">
                    <p className="font-bold uppercase tracking-wider text-text-primary mb-0.5">
                      No Error · No Signal
                    </p>
                    <p className="text-text-secondary leading-relaxed">
                      {currentResult.note} To an offline brute-force attacker holding the database, this
                      decoy is indistinguishable from a legitimate user vault. The attacker must test every
                      credential against live servers — triggering rate limits and account lockouts.
                    </p>
                  </div>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </section>

      {/* ── 3. THE LASTPASS STORY SECTION ─────────────────────────── */}
      <section className="relative z-10 py-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto border-t border-border">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <Badge variant="destructive" className="mb-3">
            Case Study: The 2022 LastPass Breach
          </Badge>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-text-primary mb-4">
            The $35M Flaw in Conventional Vaults
          </h2>
          <p className="text-text-secondary text-base leading-relaxed">
            In August and November 2022, threat actors breached LastPass cloud storage and exfiltrated
            encrypted customer vault backups. What happened next exposed the fatal limitation of conventional
            cryptography.
          </p>
        </div>

        {/* 3 Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-14">
          <Card className="border-border bg-bg-surface/90 hover:border-danger/40 transition-colors">
            <CardHeader className="pb-2">
              <span className="text-3xl sm:text-4xl font-black text-danger">25M+</span>
              <CardTitle className="text-base font-bold text-text-primary">
                Customer Vaults Exfiltrated
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-text-secondary text-sm">
                Attackers acquired complete encrypted database backups. Once stored locally, they bypassed
                all online rate limits and multi-factor authentication entirely.
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="border-border bg-bg-surface/90 hover:border-danger/40 transition-colors">
            <CardHeader className="pb-2">
              <span className="text-3xl sm:text-4xl font-black text-danger">&gt;$35M</span>
              <CardTitle className="text-base font-bold text-text-primary">
                Stolen from Cracked Vaults
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-text-secondary text-sm">
                Researchers traced over 150 high-profile crypto theft victims back to stolen vaults cracked
                offline using GPU clusters targeting human-memorized master passwords.
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="border-border bg-bg-surface/90 hover:border-danger/40 transition-colors">
            <CardHeader className="pb-2">
              <span className="text-3xl sm:text-4xl font-black text-danger">$24.5M</span>
              <CardTitle className="text-base font-bold text-text-primary">
                Settlement & Fines
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-text-secondary text-sm">
                Legal settlements and international regulatory penalties followed the disclosure that
                unauthenticated metadata and predictable vault structures facilitated offline cracking.
              </CardDescription>
            </CardContent>
          </Card>
        </div>

        {/* Comparative Analysis */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Conventional Vaults */}
          <div className="rounded-xl border border-danger/30 bg-danger/5 p-6">
            <div className="flex items-center gap-2 mb-4 text-danger font-bold text-lg">
              <AlertTriangle className="w-5 h-5" />
              <span>Conventional Architecture (LastPass, KeePass)</span>
            </div>
            <ul className="space-y-3 text-sm text-text-secondary">
              <li className="flex items-start gap-2">
                <span className="text-danger font-bold">✕</span>
                <span>
                  <strong>The Verification Oracle:</strong> AES-GCM authentication tags or JSON syntax
                  checks return immediate error codes when a guessed password is wrong.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-danger font-bold">✕</span>
                <span>
                  <strong>Unrestricted Offline Guessing:</strong> Attackers run billions of guesses per
                  second on GPUs with Hashcat. The file itself confirms when a password matches.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-danger font-bold">✕</span>
                <span>
                  <strong>Human Entropy Collapse:</strong> Real human master passwords follow skewed Zipf
                  distributions, making dictionary attacks mathematically guaranteed to crack vaults.
                </span>
              </li>
            </ul>
          </div>

          {/* Honey Vaults */}
          <div className="rounded-xl border border-accent/40 bg-accent/5 p-6">
            <div className="flex items-center gap-2 mb-4 text-accent font-bold text-lg">
              <ShieldCheck className="w-5 h-5" />
              <span>HoneyVault Architecture (Juels & Ristenpart)</span>
            </div>
            <ul className="space-y-3 text-sm text-text-secondary">
              <li className="flex items-start gap-2">
                <span className="text-accent font-bold">✓</span>
                <span>
                  <strong>No Verification Oracle:</strong> AES-256-CTR with no MAC or auth tags. Every
                  possible 32-byte key stream decrypts ciphertext without raising an error.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-accent font-bold">✓</span>
                <span>
                  <strong>Distribution-Transforming Encoder (DTE):</strong> Decrypted seeds map into
                  statistically natural passwords and usernames trained on 1M+ real credentials.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-accent font-bold">✓</span>
                <span>
                  <strong>Offline Impotence:</strong> An attacker trying 1,000,000 guesses receives
                  1,000,000 valid-looking vaults. Stolen data is rendered economically useless.
                </span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── 4. HOW IT WORKS: 4-STEP PIPELINE ─────────────────────── */}
      <section className="relative z-10 py-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto border-t border-border">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <Badge variant="outline" className="mb-3 border-accent/40 text-accent bg-accent/5">
            Cryptographic Pipeline
          </Badge>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-text-primary mb-4">
            How Honey Encryption Operates
          </h2>
          <p className="text-text-secondary text-base leading-relaxed">
            By transforming the plaintext space and eliminating authentication tags, HoneyVault ensures
            decryption is a total mathematical function: any key produces a valid vault.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            {
              step: '01',
              title: 'Argon2id KDF',
              desc: 'Master password and 16-byte random salt pass through memory-hard Argon2id (t=3, m=64MB, p=4), resisting GPU/ASIC acceleration.',
              icon: Cpu,
            },
            {
              step: '02',
              title: 'AES-256-CTR No MAC',
              desc: 'Stream cipher keystream is XORed with fixed-length ciphertext. Without MAC, padding, or checksums, no verification oracle exists.',
              icon: Lock,
            },
            {
              step: '03',
              title: 'DTE Seed Transform',
              desc: 'Decrypted 532-byte seed passes into a PCFG trained on RockYou and common domains, mapping uniform ints to natural credentials.',
              icon: Layers,
            },
            {
              step: '04',
              title: 'Plausible Vault',
              desc: 'The result is a structurally perfect vault with valid services, realistic usernames, plausible passwords, and a visual Sigil.',
              icon: CheckCircle2,
            },
          ].map((step, idx) => {
            const Icon = step.icon;
            return (
              <div
                key={idx}
                className="relative rounded-xl border border-border bg-bg-surface p-6 flex flex-col justify-between hover:border-accent/40 transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-mono font-bold text-accent px-2 py-1 rounded bg-accent/10 border border-accent/20">
                      STEP {step.step}
                    </span>
                    <Icon className="w-5 h-5 text-text-muted" />
                  </div>
                  <h3 className="text-base font-bold text-text-primary mb-2">{step.title}</h3>
                  <p className="text-xs sm:text-sm text-text-secondary leading-relaxed">{step.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── 5. FEATURE GRID ───────────────────────────────────────── */}
      <section className="relative z-10 py-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto border-t border-border">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <Badge variant="outline" className="mb-3 border-accent/40 text-accent bg-accent/5">
            Full-Spectrum Defense
          </Badge>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-text-primary mb-4">
            Engineered Beyond Academic Theory
          </h2>
          <p className="text-text-secondary text-base leading-relaxed">
            HoneyVault integrates Honey Encryption with honeywords tripwires, elliptic-curve credential
            sharing, and an in-house PKI to deliver an end-to-end security suite.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[
            {
              title: 'Honey Vault Core',
              subtitle: 'PCFG DTE + Stream Cipher',
              desc: 'Probabilistic Context-Free Grammar trained on 1M+ real passwords. Total decoding guarantee ensures 100% of seeds yield valid, printable credentials.',
              icon: ShieldCheck,
            },
            {
              title: 'Vault Sigil',
              subtitle: 'Visual Typo Awareness',
              desc: 'A deterministic 3-emoji fingerprint + color derived from your master key. Allows the authentic user to immediately notice a typo without giving attackers an oracle.',
              icon: Fingerprint,
            },
            {
              title: 'Honeywords Breach Alarm',
              subtitle: 'Juels-Rivest Sweetwords',
              desc: 'Auth database stores k sweetwords per user (1 real + honeywords). An isolated honeychecker microservice triggers immediate breach alarms if a decoy is tested.',
              icon: ShieldAlert,
            },
            {
              title: 'ECDH / ECDSA Sharing',
              subtitle: 'End-to-End Cryptography',
              desc: 'Share individual credentials securely using ephemeral ECDH (P-256) key exchange, HKDF derivation, AES-GCM envelope encryption, and ECDSA digital signatures.',
              icon: Share2,
            },
            {
              title: 'Mini PKI + mTLS',
              subtitle: 'Zero-Trust Service Mesh',
              desc: 'Integrated 2-tier X.509 Certificate Authority (Root CA + Issuing CA) providing user identity certificates and mutual TLS authentication between microservices.',
              icon: Network,
            },
            {
              title: 'Attack Lab & Evaluator',
              subtitle: 'Real-Time Cracking Harness',
              desc: 'Live offline brute-force simulator comparing dictionary attacks against conventional AES-GCM vs HoneyVault, alongside chi-squared uniformity test reports.',
              icon: FlaskConical,
            },
          ].map((feat, idx) => {
            const Icon = feat.icon;
            return (
              <Card
                key={idx}
                className="border-border bg-bg-surface/80 hover:border-accent/40 transition-all hover:shadow-card"
              >
                <CardHeader>
                  <div className="w-10 h-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center mb-3">
                    <Icon className="w-5 h-5 text-accent" />
                  </div>
                  <CardTitle className="text-lg font-bold text-text-primary">{feat.title}</CardTitle>
                  <span className="text-xs font-medium text-accent">{feat.subtitle}</span>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-text-secondary text-xs sm:text-sm leading-relaxed">
                    {feat.desc}
                  </CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* ── 6. FINAL CALL TO ACTION (CTA) ─────────────────────────── */}
      <section className="relative z-10 py-20 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto">
        <div className="relative rounded-2xl border border-accent/30 bg-gradient-to-b from-bg-surface to-bg-elevated p-8 sm:p-14 text-center overflow-hidden shadow-elevated">
          {/* Accent Glow */}
          <div
            className="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-96 bg-accent/15 rounded-full blur-3xl pointer-events-none"
            aria-hidden="true"
          />

          <Badge variant="outline" className="mb-4 border-accent/40 text-accent bg-accent/10">
            Get Started
          </Badge>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-text-primary tracking-tight mb-4">
            Ready to neutralize offline vault cracking?
          </h2>
          <p className="text-text-secondary text-base sm:text-lg max-w-2xl mx-auto mb-8 leading-relaxed">
            Create your HoneyVault account to experience uncrackable offline storage, or launch the
            interactive Attack Lab to simulate dictionary attacks on stolen vaults.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4">
            <Button asChild size="lg" className="rounded-xl px-8 py-6 text-base shadow-glow">
              <Link to="/register" className="flex items-center gap-2">
                Register Free Vault
                <ArrowRight className="w-4 h-4" />
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              size="lg"
              className="rounded-xl px-8 py-6 text-base border-border hover:bg-bg-elevated text-text-primary"
            >
              <Link to="/attack" className="flex items-center gap-2">
                <FlaskConical className="w-4 h-4 text-accent" />
                Attack Simulator
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ── 7. LANDING FOOTER CALLOUT ─────────────────────────────── */}
      <div className="relative z-10 py-8 px-4 border-t border-border/60 text-center text-xs text-text-muted">
        <p>
          HoneyVault · Developed by <strong>Team Ocean's 10</strong> for Applied Cryptography & Network
          Security Design Challenge (ACNS-DC 2026-27), Sardar Patel Institute of Technology, Mumbai.
        </p>
      </div>
    </div>
  );
}
