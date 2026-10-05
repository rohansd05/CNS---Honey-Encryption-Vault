// owner: Chetan (T3) — Step 2: Dictionary Attack Simulation (feat/t3-attack-lab)
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Play,
  RotateCcw,
  ArrowRight,
  ArrowLeft,
  Eye,
  Sliders,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { useRunDictionaryAttack } from '@/api/hooks/useAttackQueries';
import type { DictionaryAttackResponse, DictionaryAttackHoneySample, CrackedEntry } from '@/api/types';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';

interface Step2DictionaryAttackProps {
  onNext: () => void;
  onPrev: () => void;
}

const PRESET_GUESSES = [250, 500, 1000, 2000];

export function Step2DictionaryAttack({ onNext, onPrev }: Step2DictionaryAttackProps) {
  const shouldReduceMotion = useReducedMotion();
  const runAttackMutation = useRunDictionaryAttack();

  // Attack parameters
  const [guessCount, setGuessCount] = useState<number>(1000);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simCompleted, setSimCompleted] = useState<boolean>(false);

  // Counters for the racing effect
  const [conventionalCounter, setConventionalCounter] = useState<number>(0);
  const [honeyCounter, setHoneyCounter] = useState<number>(0);

  // Attack result data
  const [attackResult, setAttackResult] = useState<DictionaryAttackResponse | null>(null);

  // Honey decoy sample viewer
  const [currentSampleIndex, setCurrentSampleIndex] = useState<number>(0);

  // Animation frame / timer references
  const animFrameRef = useRef<number | null>(null);
  const cycleIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (cycleIntervalRef.current) clearInterval(cycleIntervalRef.current);
    };
  }, []);

  // Auto-cycle through decoy samples while simulating or when complete
  useEffect(() => {
    if (!attackResult?.honey.samples.length) return;

    const intervalTime = shouldReduceMotion ? 2500 : 1200;
    cycleIntervalRef.current = setInterval(() => {
      setCurrentSampleIndex((prev) => (prev + 1) % attackResult.honey.samples.length);
    }, intervalTime);

    return () => {
      if (cycleIntervalRef.current) clearInterval(cycleIntervalRef.current);
    };
  }, [attackResult, shouldReduceMotion]);

  const handleLaunchAttack = async () => {
    setIsSimulating(true);
    setSimCompleted(false);
    setConventionalCounter(0);
    setHoneyCounter(0);
    setCurrentSampleIndex(0);

    try {
      const data = await runAttackMutation.mutateAsync({ max_guesses: guessCount });
      setAttackResult(data);

      if (shouldReduceMotion) {
        // Reduced motion: jump straight to target values
        setConventionalCounter(data.baseline.guess_index ?? guessCount);
        setHoneyCounter(data.honey.guesses_tried);
        setIsSimulating(false);
        setSimCompleted(true);
        toast.success(`Completed ${guessCount.toLocaleString()} dictionary guesses`);
        return;
      }

      // Cinematic racing counters
      const targetBaseline = data.baseline.guess_index ?? guessCount;
      const targetHoney = data.honey.guesses_tried;
      const durationMs = 2400; // 2.4s simulation race
      const startTime = performance.now();

      const updateFrame = (now: number) => {
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / durationMs);

        // Ease-out progress
        const ease = 1 - Math.pow(1 - progress, 2);

        const curHoney = Math.floor(targetHoney * ease);
        setHoneyCounter(curHoney);

        // Baseline stops early if cracked at targetBaseline
        if (data.baseline.cracked) {
          const baselineFraction = targetBaseline / targetHoney;
          if (ease >= baselineFraction) {
            setConventionalCounter(targetBaseline);
          } else {
            setConventionalCounter(Math.floor(targetBaseline * (ease / baselineFraction)));
          }
        } else {
          setConventionalCounter(Math.floor(targetBaseline * ease));
        }

        if (progress < 1) {
          animFrameRef.current = requestAnimationFrame(updateFrame);
        } else {
          setConventionalCounter(targetBaseline);
          setHoneyCounter(targetHoney);
          setIsSimulating(false);
          setSimCompleted(true);
          toast.success(`Dictionary attack finished: ${guessCount.toLocaleString()} guesses tested`);
        }
      };

      animFrameRef.current = requestAnimationFrame(updateFrame);
    } catch {
      setIsSimulating(false);
      toast.error('Simulation request failed. Check server/mock connection.');
    }
  };

  const handleResetSimulation = () => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    setIsSimulating(false);
    setSimCompleted(false);
    setConventionalCounter(0);
    setHoneyCounter(0);
    setAttackResult(null);
  };

  const currentSample: DictionaryAttackHoneySample | undefined =
    attackResult?.honey.samples[currentSampleIndex];

  return (
    <motion.div
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-6"
    >
      {/* Step Context & Control Bar */}
      <div className="rounded-xl border border-border bg-bg-surface p-6 shadow-card space-y-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/20 text-xs font-bold text-accent">
                2
              </span>
              <h2 className="text-xl font-bold text-text-primary">
                Offline Dictionary Attack Simulation
              </h2>
            </div>
            <p className="text-sm text-text-secondary max-w-2xl leading-relaxed">
              Watch what happens when an attacker brute-forces both vaults with high-frequency password guesses.
              Conventional encryption reveals the true password at the first matching tag, while Honey Encryption
              yields 1,000 distinct valid vaults with <strong>zero signal</strong>.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {simCompleted && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetSimulation}
                className="gap-1.5 border-border hover:border-accent/40 text-text-secondary hover:text-text-primary"
              >
                <RotateCcw size={14} />
                Reset
              </Button>
            )}

            <Button
              onClick={() => {
                void handleLaunchAttack();
              }}
              disabled={isSimulating}
              className="gap-2 bg-accent text-black font-semibold hover:bg-accent-hover shadow-glow"
            >
              <Play size={15} className={isSimulating ? 'animate-spin' : 'fill-black'} />
              {isSimulating
                ? 'Testing Guesses...'
                : simCompleted
                  ? 'Re-run Simulation'
                  : 'Launch Attack Simulator'}
            </Button>
          </div>
        </div>

        {/* Guess Count Slider & Presets */}
        <div className="rounded-lg bg-bg-elevated p-4 border border-border space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Sliders size={16} className="text-accent" />
              <label htmlFor="guess-slider" className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Max Dictionary Guesses:
              </label>
              <span className="font-mono text-sm font-bold text-accent">
                {guessCount.toLocaleString()}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-xs text-text-muted mr-1">Presets:</span>
              {PRESET_GUESSES.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => {
                    if (!isSimulating) setGuessCount(preset);
                  }}
                  disabled={isSimulating}
                  className={`text-xs px-2.5 py-1 rounded font-mono transition-colors ${
                    guessCount === preset
                      ? 'bg-accent text-black font-bold'
                      : 'bg-bg-surface hover:bg-bg-overlay text-text-secondary border border-border'
                  }`}
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1">
            <input
              id="guess-slider"
              type="range"
              min={100}
              max={2000}
              step={50}
              value={guessCount}
              onChange={(e) => {
                if (!isSimulating) setGuessCount(Number(e.target.value));
              }}
              disabled={isSimulating}
              className="w-full h-2 bg-bg-surface rounded-lg appearance-none cursor-pointer accent-accent border border-border"
            />
            <div className="flex justify-between text-[11px] text-text-muted font-mono">
              <span>100</span>
              <span>500</span>
              <span className="text-accent font-semibold">1,000 (Default)</span>
              <span>1,500</span>
              <span>2,000</span>
            </div>
          </div>
        </div>
      </div>

      {/* Side-by-Side Simulation Arena */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* =========================================================================
            LEFT PANEL: CONVENTIONAL VAULT (AES-256-GCM)
           ========================================================================= */}
        <Card
          className={`border bg-bg-surface shadow-card transition-all duration-300 ${
            simCompleted && attackResult?.baseline.cracked
              ? 'border-danger/60 shadow-[0_0_24px_rgba(239,68,68,0.2)]'
              : 'border-border'
          }`}
        >
          <CardHeader className="pb-3 border-b border-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-danger/20 text-danger border border-danger/30">
                  <Lock size={16} />
                </div>
                <div>
                  <CardTitle className="text-base text-text-primary">
                    Conventional Vault
                  </CardTitle>
                  <CardDescription className="text-xs">
                    AES-256-GCM with 128-bit authentication tag
                  </CardDescription>
                </div>
              </div>

              {simCompleted && attackResult?.baseline.cracked ? (
                <Badge variant="destructive" className="animate-pulse font-mono font-bold text-xs py-1 px-2.5">
                  CRACKED AT GUESS #{String(attackResult.baseline.guess_index ?? 137)}
                </Badge>
              ) : isSimulating ? (
                <Badge variant="secondary" className="font-mono text-xs">
                  TESTING GUESSES...
                </Badge>
              ) : (
                <Badge variant="outline" className="font-mono text-xs text-text-muted">
                  IDLE
                </Badge>
              )}
            </div>
          </CardHeader>

          <CardContent className="p-5 space-y-4">
            {/* Speedometer / Digital Counter */}
            <div className="rounded-xl bg-bg-elevated p-4 border border-border flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="text-xs uppercase tracking-wider text-text-muted">Guesses Verified</span>
                <div className="font-mono text-2xl font-black text-text-primary">
                  {conventionalCounter.toLocaleString()}{' '}
                  <span className="text-xs text-text-muted font-normal">
                    / {guessCount.toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="text-right space-y-0.5">
                <span className="text-xs uppercase tracking-wider text-text-muted">Decryption Oracle</span>
                <div
                  className={`font-mono text-xs font-bold ${
                    simCompleted && attackResult?.baseline.cracked
                      ? 'text-danger flex items-center gap-1 justify-end'
                      : 'text-text-secondary'
                  }`}
                >
                  {simCompleted && attackResult?.baseline.cracked ? (
                    <>
                      <ShieldAlert size={14} /> TAG MATCH FOUND
                    </>
                  ) : (
                    'TAG MISMATCH (0 / 128 bit)'
                  )}
                </div>
                <div className="text-[11px] text-text-muted font-mono">
                  {simCompleted
                    ? `Time: ${String(attackResult?.baseline.elapsed_ms ?? 812)}ms`
                    : isSimulating
                      ? 'Calculating...'
                      : '0ms'}
                </div>
              </div>
            </div>

            {/* Oracle explanation card */}
            <div className="rounded-lg bg-danger/10 p-3.5 border border-danger/20 text-xs space-y-1.5">
              <div className="font-bold text-danger flex items-center gap-1.5">
                <AlertTriangle size={14} />
                Decryption Oracle Confirmed Password
              </div>
              <p className="text-text-secondary leading-normal">
                At guess #{String(attackResult?.baseline.guess_index ?? 137)}, the AES-GCM Poly1305 authentication tag verified with 100% precision.
                The cracking engine halted immediately.
              </p>
            </div>

            {/* Plaintext Recovered Entries */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                  Recovered Plaintext Credentials
                </span>
                <span className="text-xs text-text-muted font-mono">
                  {simCompleted && attackResult?.baseline.cracked
                    ? `${String(attackResult.baseline.recovered_entries.length)} entries exposed`
                    : 'Encrypted'}
                </span>
              </div>

              {simCompleted && attackResult?.baseline.cracked ? (
                <div className="rounded-lg border border-danger/30 overflow-hidden bg-bg-surface">
                  <Table>
                    <TableHeader className="bg-bg-elevated/70">
                      <TableRow className="border-border">
                        <TableHead className="text-xs h-8 text-text-muted">Service</TableHead>
                        <TableHead className="text-xs h-8 text-text-muted">Username</TableHead>
                        <TableHead className="text-xs h-8 text-danger font-semibold">Decrypted Password</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {attackResult.baseline.recovered_entries.map((entry: CrackedEntry) => (
                        <TableRow key={entry.id} className="border-border/60 font-mono text-xs">
                          <TableCell className="font-semibold text-text-primary py-2">
                            {entry.service}
                          </TableCell>
                          <TableCell className="text-text-secondary py-2">
                            {entry.username}
                          </TableCell>
                          <TableCell className="text-danger font-bold py-2 bg-danger/5">
                            {entry.password}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="h-44 rounded-lg border border-dashed border-border flex flex-col items-center justify-center p-4 text-center text-text-muted space-y-2 bg-bg-elevated/30">
                  <Lock size={24} className="text-border" />
                  <p className="text-xs max-w-xs">
                    {isSimulating
                      ? 'Testing dictionary candidates against AES-GCM tag...'
                      : 'Launch attack to verify how the authentication tag exposes the vault.'}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* =========================================================================
            RIGHT PANEL: HONEY VAULT (HE-PCFG-V1)
           ========================================================================= */}
        <Card
          className={`border bg-bg-surface shadow-card transition-all duration-300 ${
            simCompleted
              ? 'border-accent/60 shadow-[0_0_24px_rgba(245,165,36,0.18)]'
              : 'border-border'
          }`}
        >
          <CardHeader className="pb-3 border-b border-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-md bg-accent/20 text-accent border border-accent/30">
                  <ShieldCheck size={16} />
                </div>
                <div>
                  <CardTitle className="text-base text-text-primary">
                    Honey Vault (HE-PCFG)
                  </CardTitle>
                  <CardDescription className="text-xs">
                    AES-256-CTR + PCFG Distribution-Transforming Encoder
                  </CardDescription>
                </div>
              </div>

              {simCompleted ? (
                <Badge className="bg-accent text-black font-mono font-bold text-xs py-1 px-2.5 shadow-glow">
                  0 SIGNAL / ZERO ORACLE
                </Badge>
              ) : isSimulating ? (
                <Badge variant="secondary" className="font-mono text-xs text-accent">
                  STREAMING DECOYS...
                </Badge>
              ) : (
                <Badge variant="outline" className="font-mono text-xs text-text-muted">
                  IDLE
                </Badge>
              )}
            </div>
          </CardHeader>

          <CardContent className="p-5 space-y-4">
            {/* Speedometer / Digital Counter */}
            <div className="rounded-xl bg-bg-elevated p-4 border border-border flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="text-xs uppercase tracking-wider text-text-muted">Vaults Decoded</span>
                <div className="font-mono text-2xl font-black text-accent">
                  {honeyCounter.toLocaleString()}{' '}
                  <span className="text-xs text-text-muted font-normal">
                    / {guessCount.toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="text-right space-y-0.5">
                <span className="text-xs uppercase tracking-wider text-text-muted">Oracle Signal</span>
                <div className="font-mono text-xs font-bold text-success flex items-center gap-1 justify-end">
                  <ShieldCheck size={14} /> ZERO LEAKAGE
                </div>
                <div className="text-[11px] text-text-muted font-mono">
                  {simCompleted
                    ? `Distinct Vaults: ${attackResult?.honey.distinct_vaults.toLocaleString() ?? ''}`
                    : isSimulating
                      ? 'Generating valid decoys...'
                      : '100% Total Decode'}
                </div>
              </div>
            </div>

            {/* Zero Signal explanation card */}
            <div className="rounded-lg bg-accent/10 p-3.5 border border-accent/30 text-xs space-y-1.5">
              <div className="font-bold text-accent flex items-center gap-1.5">
                <Sparkles size={14} />
                Maximum Attacker Confusion
              </div>
              <p className="text-text-secondary leading-normal">
                Every single password guess produced a completely well-formed, plausible vault.
                The attacker has <strong>{guessCount.toLocaleString()} candidate vaults</strong> and
                mathematically zero bits of information on which one is authentic!
              </p>
            </div>

            {/* Animated Decoy Stream & Sample Carousel */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                    Decoy Vault Stream
                  </span>
                  {attackResult && (
                    <Badge variant="outline" className="font-mono text-[10px] text-text-muted">
                      Sample #{String(currentSampleIndex + 1)} of {String(attackResult.honey.samples.length)}
                    </Badge>
                  )}
                </div>

                {attackResult && (
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => {
                        setCurrentSampleIndex((prev) =>
                          prev === 0 ? attackResult.honey.samples.length - 1 : prev - 1,
                        );
                      }}
                      className="p-1 rounded hover:bg-bg-elevated text-text-secondary hover:text-text-primary border border-border"
                      aria-label="Previous sample"
                    >
                      <ChevronLeft size={14} />
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setCurrentSampleIndex((prev) =>
                          (prev + 1) % attackResult.honey.samples.length,
                        );
                      }}
                      className="p-1 rounded hover:bg-bg-elevated text-text-secondary hover:text-text-primary border border-border"
                      aria-label="Next sample"
                    >
                      <ChevronRight size={14} />
                    </button>
                  </div>
                )}
              </div>

              {currentSample ? (
                <div className="rounded-lg border border-accent/40 bg-bg-surface overflow-hidden shadow-sm">
                  <div className="bg-bg-elevated/90 px-3 py-2 border-b border-border flex items-center justify-between text-xs font-mono">
                    <div className="flex items-center gap-1.5">
                      <span className="text-text-muted">Guess #{String(currentSample.guess_index)}:</span>
                      <span className="font-bold text-accent">"{currentSample.guess}"</span>
                    </div>
                    <Badge variant="outline" className="text-[10px] text-success border-success/40">
                      Valid Decoy Plaintext
                    </Badge>
                  </div>

                  <Table>
                    <TableHeader className="bg-bg-elevated/40">
                      <TableRow className="border-border">
                        <TableHead className="text-xs h-7 text-text-muted">Service</TableHead>
                        <TableHead className="text-xs h-7 text-text-muted">Decoy Username</TableHead>
                        <TableHead className="text-xs h-7 text-accent font-semibold">Decoy Password</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {currentSample.entries.map((entry) => (
                        <TableRow key={entry.id} className="border-border/40 font-mono text-xs">
                          <TableCell className="font-medium text-text-primary py-1.5">
                            {entry.service}
                          </TableCell>
                          <TableCell className="text-text-secondary py-1.5">
                            {entry.username}
                          </TableCell>
                          <TableCell className="text-accent py-1.5">
                            {entry.password}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="h-44 rounded-lg border border-dashed border-border flex flex-col items-center justify-center p-4 text-center text-text-muted space-y-2 bg-bg-elevated/30">
                  <Sparkles size={24} className="text-accent/40" />
                  <p className="text-xs max-w-xs">
                    {isSimulating
                      ? 'Generating PCFG plausible decoy vaults...'
                      : 'Launch attack to see how every wrong password yields natural decoys.'}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* =========================================================================
          THE BIG REVEAL (Rendered when simulation completes)
         ========================================================================= */}
      <AnimatePresence>
        {simCompleted && attackResult && (
          <motion.div
            initial={{ opacity: 0, scale: shouldReduceMotion ? 1 : 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="rounded-xl border-2 border-accent bg-bg-surface p-6 shadow-glow space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-accent text-black font-bold">
                  <Eye size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-text-primary">
                    The Grand Reveal: Where Was the Real Master Password?
                  </h3>
                  <p className="text-xs text-text-secondary">
                    Compare the true vault against the decoy stream
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-accent text-accent font-mono text-xs px-2.5 py-1">
                  Real Guess Index: #{String(attackResult.reveal.real_guess_index ?? 137)}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div className="rounded-lg bg-bg-elevated p-4 border border-border space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-accent">Guess #0: "123456"</span>
                  <Badge variant="outline" className="text-[10px] text-text-muted">Decoy #1</Badge>
                </div>
                <div className="font-mono text-xs text-text-secondary space-y-1">
                  <div>github.com: <span className="text-text-primary">dragon88</span></div>
                  <div>proton.me: <span className="text-text-primary">summer2019!</span></div>
                  <div>aws: <span className="text-text-primary">monkey1234</span></div>
                </div>
                <div className="text-[11px] text-text-muted pt-1">
                  Grammar: L6D2, L6S1, L6D4
                </div>
              </div>

              <div className="rounded-lg bg-accent/15 p-4 border-2 border-accent space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-accent">
                    Guess #137: "correct horse..."
                  </span>
                  <Badge className="bg-accent text-black font-bold text-[10px]">Real Vault</Badge>
                </div>
                <div className="font-mono text-xs text-text-primary space-y-1">
                  <div>github.com: <span className="text-accent font-semibold">ghp_K992jSkA...</span></div>
                  <div>proton.me: <span className="text-accent font-semibold">Tr0ub4dor&3#Priv</span></div>
                  <div>aws: <span className="text-accent font-semibold">AKIAIOSFODNN7...</span></div>
                </div>
                <div className="text-[11px] text-accent font-medium pt-1">
                  Authentic credentials of @demo
                </div>
              </div>

              <div className="rounded-lg bg-bg-elevated p-4 border border-border space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-accent">Guess #24: "dragon"</span>
                  <Badge variant="outline" className="text-[10px] text-text-muted">Decoy #25</Badge>
                </div>
                <div className="font-mono text-xs text-text-secondary space-y-1">
                  <div>github.com: <span className="text-text-primary">matrix2022</span></div>
                  <div>proton.me: <span className="text-text-primary">phantom#4</span></div>
                  <div>aws: <span className="text-text-primary">silverado9</span></div>
                </div>
                <div className="text-[11px] text-text-muted pt-1">
                  Grammar: L6D4, L7S1D1
                </div>
              </div>
            </div>

            <div className="rounded-lg bg-bg-elevated/70 p-3.5 border border-border flex items-start gap-2.5 text-xs text-text-secondary leading-relaxed">
              <CheckCircle2 size={16} className="text-accent mt-0.5 shrink-0" />
              <span>
                <strong>Conclusion for Attacker:</strong> Because the DTE samples decoy passwords from the exact same
                statistical PCFG distribution as genuine human choices, Guess #137 looked <em>no different</em> than
                Guess #0 or Guess #24. To find out which vault is real, the attacker must attempt to use these credentials online,
                triggering active tripwires.
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stepper Navigation Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-border">
        <Button
          variant="outline"
          onClick={onPrev}
          disabled={isSimulating}
          className="gap-2 border-border hover:border-accent/40 text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft size={16} />
          Back to Vault Exfiltration
        </Button>

        <Button
          onClick={onNext}
          disabled={isSimulating}
          className="gap-2 bg-accent text-black font-semibold hover:bg-accent-hover shadow-glow"
        >
          Proceed to Honeywords & Login
          <ArrowRight size={16} />
        </Button>
      </div>
    </motion.div>
  );
}
