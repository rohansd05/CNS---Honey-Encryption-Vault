// owner: Krrish (T3) — animated honeycomb/ocean illustration for auth split layout
import { motion } from 'framer-motion';
import { Shield, KeyRound, Sparkles, Lock } from 'lucide-react';

interface AuthIllustrationProps {
  mode: 'login' | 'register';
}

export function AuthIllustration({ mode }: AuthIllustrationProps) {
  return (
    <div className="relative hidden lg:flex flex-col justify-between overflow-hidden rounded-2xl bg-gradient-to-br from-[#0c192c] via-[#09111e] to-[#050b14] border border-[var(--border)] p-10 text-white shadow-2xl">
      {/* Background glow effects */}
      <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full bg-amber-500/10 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 h-96 w-96 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />

      {/* SVG Honeycomb Graphic */}
      <div className="absolute inset-0 opacity-15 pointer-events-none">
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="hex-pattern" width="56" height="96" patternUnits="userSpaceOnUse" patternTransform="scale(1)">
              <path
                d="M28 0 L56 16 L56 48 L28 64 L0 48 L0 16 Z M28 48 L56 64 L56 96 L28 112 L0 96 L0 64 Z"
                fill="none"
                stroke="#f5a524"
                strokeWidth="1.2"
                strokeOpacity="0.4"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#hex-pattern)" />
        </svg>
      </div>

      {/* Top Header */}
      <div className="relative z-10 space-y-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3.5 py-1 text-xs font-medium text-amber-300 backdrop-blur-md">
          <Sparkles className="h-3.5 w-3.5 text-amber-400" />
          <span>Honey Encryption Vault</span>
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-white lg:text-3xl">
          {mode === 'login' ? 'Zero Verification Oracle' : 'Every Guess Yields a Plausible Vault'}
        </h2>
        <p className="text-sm text-slate-300 leading-relaxed max-w-md">
          {mode === 'login'
            ? 'Even if the database is exfiltrated, offline attackers cannot distinguish true credentials from statistical decoys.'
            : 'Separate your account login password from your vault encryption password. Your master password never leaves your browser unencrypted.'}
        </p>
      </div>

      {/* Center Interactive Visualization Card */}
      <div className="relative z-10 my-8">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="rounded-xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl shadow-xl space-y-4"
        >
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30">
                <Shield className="h-4 w-4" />
              </div>
              <span className="font-mono text-xs font-semibold tracking-wider text-slate-200">
                VAULT SIGIL PREVIEW
              </span>
            </div>
            <span className="text-[11px] font-mono text-amber-400/90 bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/20">
              AES-256-CTR
            </span>
          </div>

          <div className="flex items-center justify-between gap-4 p-3.5 rounded-lg bg-black/40 border border-white/5">
            <div className="flex items-center gap-3">
              <span className="text-2xl select-none" role="img" aria-label="sigil-preview">🍯 🐝 🛡️</span>
              <div>
                <div className="text-xs font-semibold text-white">Your Unique Vault Sigil</div>
                <div className="text-[11px] text-slate-400 font-mono">Recognize your 3-emoji key visual</div>
              </div>
            </div>
            <div className="h-4 w-4 rounded-full bg-[#f5a524] ring-4 ring-amber-500/20" />
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="rounded-lg bg-slate-800/50 p-2.5 border border-white/5">
              <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-medium mb-1">
                <KeyRound className="h-3 w-3" /> Right Master Key
              </div>
              <p className="text-[11px] text-slate-300 font-mono">Authentic Passwords + Authentic Sigil</p>
            </div>
            <div className="rounded-lg bg-slate-800/50 p-2.5 border border-white/5">
              <div className="flex items-center gap-1.5 text-[11px] text-amber-400 font-medium mb-1">
                <Lock className="h-3 w-3" /> Wrong Master Key
              </div>
              <p className="text-[11px] text-slate-300 font-mono">Plausible Decoy Vault + Changed Sigil</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Bottom Security Footer Highlights */}
      <div className="relative z-10 grid grid-cols-3 gap-3 border-t border-white/10 pt-6">
        <div>
          <div className="text-xs font-semibold text-white">Argon2id</div>
          <div className="text-[11px] text-slate-400">Memory-hard KDF</div>
        </div>
        <div>
          <div className="text-xs font-semibold text-white">PCFG DTE</div>
          <div className="text-[11px] text-slate-400">Total Decoy Decoder</div>
        </div>
        <div>
          <div className="text-xs font-semibold text-white">Honeywords</div>
          <div className="text-[11px] text-slate-400">Breach Alarm System</div>
        </div>
      </div>
    </div>
  );
}
