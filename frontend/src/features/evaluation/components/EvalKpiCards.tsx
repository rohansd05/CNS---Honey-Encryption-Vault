// owner: Chetan (T3) — KPI cards (feat/t3-eval-real-data)
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  BrainCircuit,
  Binary,
  ShieldAlert,
  HelpCircle,
  AlertTriangle,
  ExternalLink,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import type { EvalSummaryData } from '../types';

interface EvalKpiCardsProps {
  data: EvalSummaryData;
}

function formatPValue(p: number | undefined): string {
  if (p === undefined) return 'N/A';
  if (p <= 1e-300) return '< 1e-300';
  if (p < 0.001) {
    const exp = p.toExponential(1);
    return exp.replace('e', ' × 10^');
  }
  return p.toFixed(3);
}

export function EvalKpiCards({ data }: EvalKpiCardsProps) {
  const cardVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { duration: 0.35, delay: i * 0.08 },
    }),
  };

  // Card 1 values
  const roundTrip = data.round_trip;
  const roundTripPercent = (roundTrip.success_rate * 100).toFixed(1);
  const totalityPercent = (roundTrip.decode_totality.totality_rate * 100).toFixed(1);

  // Card 2 values
  const accuracy = data.distinguisher.metrics.accuracy;
  const accuracyPercent = (accuracy * 100).toFixed(1);
  const target = data.distinguisher.target_accuracy;
  const targetPercent = (target * 100).toFixed(0);
  const isAboveTarget = accuracy > target;
  const distinctResults = data.distinguisher.distinct_results;
  const bestDistinctAccuracy = distinctResults
    ? Math.max(
        distinctResults.logreg?.accuracy_mean ?? 0,
        distinctResults.random_forest?.accuracy_mean ?? 0,
      )
    : null;

  // Card 3 values
  const alpha = data.chi_squared.alpha ?? 0.05;
  const isPit = data.chi_squared.password?.seed_pit_uniformity !== undefined;
  const seedTestLabel = isPit ? 'PIT' : 'Byte';
  const seedP =
    data.chi_squared.password?.seed_pit_uniformity?.p_value ??
    data.chi_squared.password?.seed_byte_uniformity?.p_value ??
    data.chi_squared.seed_uniformity?.p_value;
  const controlP = isPit
    ? (data.chi_squared.password?.seed_pit_uniformity_control?.p_value ??
       data.chi_squared.password?.seed_int_uniformity_control?.p_value)
    : data.chi_squared.password?.seed_int_uniformity_control?.p_value;
  const templateP =
    data.chi_squared.password?.template_goodness_of_fit?.p_value ??
    data.chi_squared.template_goodness_of_fit?.p_value;
  const seedPass = seedP !== undefined && seedP > alpha;
  const templatePass = templateP !== undefined && templateP > alpha;

  // Card 4 values
  const attack = data.attack;
  const guessIndex = attack?.conventional.guess_index;
  const totalGuesses = attack?.guesses;
  const distinctVaults = attack?.honey.distinct_vaults;

  return (
    <TooltipProvider>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Round-Trip & Totality */}
        <motion.div custom={0} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="h-full border-border bg-bg-surface hover:border-accent/40 transition-all duration-200 shadow-card relative overflow-hidden group">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-success to-emerald-400" />
            <CardContent className="p-5 flex flex-col justify-between h-full space-y-3">
              <div className="flex items-start justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Round-Trip Invertibility
                </span>
                <div className="p-2 rounded-lg bg-success/10 text-success">
                  <CheckCircle2 size={18} />
                </div>
              </div>

              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-text-primary tracking-tight font-mono">
                    {roundTripPercent}%
                  </span>
                  <Badge variant="outline" className="bg-success/15 text-success border-success/30 text-[11px] font-semibold">
                    {roundTrip.success_rate === 1.0 ? '100% Lossless' : `${roundTripPercent}% Exact`}
                  </Badge>
                </div>
                <p className="text-xs text-text-secondary mt-1">
                  {roundTrip.exact_match_count.toLocaleString()} / {roundTrip.trials.toLocaleString()} verified trials
                </p>
              </div>

              <div className="pt-2.5 border-t border-border/60 flex items-center justify-between text-xs text-text-muted">
                <span>Decode totality:</span>
                <span className="font-mono text-text-primary font-medium">
                  {totalityPercent}% ({String(roundTrip.decode_totality.failed_decodes)} errors)
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* KPI 2: Distinguisher Classifier Accuracy */}
        <motion.div custom={1} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="h-full border-border bg-bg-surface hover:border-accent/40 transition-all duration-200 shadow-card relative overflow-hidden group">
            <div
              className={`absolute top-0 left-0 right-0 h-1 ${
                isAboveTarget ? 'bg-amber-500' : 'bg-gradient-to-r from-accent to-blue-500'
              }`}
            />
            <CardContent className="p-5 flex flex-col justify-between h-full space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                    Classifier Accuracy
                  </span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button className="text-text-muted hover:text-text-primary" aria-label="Classifier info">
                        <HelpCircle size={13} />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      Evaluates whether an ML distinguisher can distinguish decrypted real vaults from synthetic honey decoys. Ideal score is 50.0% (random coin-flip guessing). Target bound is ≤ {targetPercent}%.
                    </TooltipContent>
                  </Tooltip>
                </div>
                <div className={`p-2 rounded-lg ${isAboveTarget ? 'bg-amber-500/10 text-amber-500' : 'bg-accent/10 text-accent'}`}>
                  {isAboveTarget ? <AlertTriangle size={18} /> : <BrainCircuit size={18} />}
                </div>
              </div>

              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-text-primary tracking-tight font-mono">
                    {accuracyPercent}%
                  </span>
                  {isAboveTarget ? (
                    <Badge
                      variant="outline"
                      className="bg-amber-500/15 text-amber-500 border-amber-500/30 text-[11px] font-semibold"
                    >
                      Above Target
                    </Badge>
                  ) : (
                    <Badge
                      variant="outline"
                      className="bg-info/15 text-info border-info/30 text-[11px] font-semibold"
                    >
                      ≤ {targetPercent}% Bound
                    </Badge>
                  )}
                </div>
                {isAboveTarget ? (
                  <div className="text-xs text-amber-500/90 mt-1 flex items-start gap-1">
                    <span>
                      Exceeds target ({accuracyPercent}% vs ≤{targetPercent}%){bestDistinctAccuracy !== null ? `; drops to ${(bestDistinctAccuracy * 100).toFixed(1)}% on distinct strings.` : ' due to repeated strings across folds.'}
                    </span>
                    <a
                      href="https://github.com/rohansd05/CNS---Honey-Encryption-Vault/blob/dev/docs/eval-report.md#43-distinguisher-0741-overall-mostly-from-repeated-strings-partly-from-real-mismatch"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline hover:text-amber-400 font-semibold inline-flex items-center gap-0.5 shrink-0"
                    >
                      <span>docs</span>
                      <ExternalLink size={10} />
                    </a>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 text-xs text-text-secondary mt-1">
                    <span className="inline-block w-2 h-2 rounded-full bg-accent" />
                    <span>Reference: <strong>{(data.distinguisher.ideal_accuracy * 100).toFixed(0)}%</strong> (Random Guessing)</span>
                  </div>
                )}
              </div>

              <div className="pt-2.5 border-t border-border/60 flex items-center justify-between text-xs text-text-muted">
                <span>Distinguisher:</span>
                <span className="font-mono text-text-primary font-medium truncate max-w-[150px]">
                  {data.distinguisher.metrics_classifier ?? 'LR + RF'}{' '}
                  (AUC: {data.distinguisher.metrics.roc_auc.toFixed(3)})
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* KPI 3: Chi-Squared Uniformity & Fit */}
        <motion.div custom={2} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="h-full border-border bg-bg-surface hover:border-accent/40 transition-all duration-200 shadow-card relative overflow-hidden group">
            <div
              className={`absolute top-0 left-0 right-0 h-1 ${
                seedPass ? 'bg-gradient-to-r from-blue-500 to-cyan-400' : 'bg-red-500'
              }`}
            />
            <CardContent className="p-5 flex flex-col justify-between h-full space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                    Chi-Squared Tests (χ²)
                  </span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button className="text-text-muted hover:text-text-primary" aria-label="Chi-squared info">
                        <HelpCircle size={13} />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      Evaluates encoded {seedTestLabel.toLowerCase()} seed uniformity (p &gt; {alpha}) and decoded template goodness-of-fit. Held-out seed uniformity fails due to model fit, while the integer codec control passes honestly.
                    </TooltipContent>
                  </Tooltip>
                </div>
                <div className="p-2 rounded-lg bg-info/10 text-info">
                  <Binary size={18} />
                </div>
              </div>

              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-extrabold text-text-primary tracking-tight font-mono">
                    {seedPass ? `${seedTestLabel} p=${formatPValue(seedP)}` : `${seedTestLabel}: FAIL`}
                  </span>
                  <Badge
                    variant="outline"
                    className={
                      seedPass
                        ? 'bg-success/15 text-success border-success/30 text-[11px] font-semibold'
                        : 'bg-red-500/15 text-red-400 border-red-500/30 text-[11px] font-semibold'
                    }
                  >
                    {seedPass ? 'PASS (p > α)' : 'FAIL (p ≤ α)'}
                  </Badge>
                </div>
                <p className="text-xs text-text-secondary mt-1">
                  {seedTestLabel} p = {formatPValue(seedP)} | Control p = {formatPValue(controlP)}
                </p>
              </div>

              <div className="pt-2.5 border-t border-border/60 flex items-center justify-between text-xs text-text-muted">
                <span>Template fit:</span>
                <span className="font-mono text-text-primary font-medium">
                  p={formatPValue(templateP)} ({templatePass ? 'PASS' : 'FAIL'})
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* KPI 4: Attack Simulation */}
        <motion.div custom={3} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="h-full border-border bg-bg-surface hover:border-accent/40 transition-all duration-200 shadow-card relative overflow-hidden group">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 to-pink-500" />
            <CardContent className="p-5 flex flex-col justify-between h-full space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                    Dictionary Attack KPI
                  </span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button className="text-text-muted hover:text-text-primary" aria-label="Attack KPI info">
                        <HelpCircle size={13} />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      Dictionary attack on conventional AES-GCM vault cracks and leaks real password index. Honey encryption returns 100% distinct plausible vaults with zero confirmation oracle.
                    </TooltipContent>
                  </Tooltip>
                </div>
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                  <ShieldAlert size={18} />
                </div>
              </div>

              {attack === undefined ? (
                <div className="py-2">
                  <Badge variant="outline" className="text-xs bg-bg-elevated text-text-muted border-border">
                    Not in this run
                  </Badge>
                </div>
              ) : (
                <div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-extrabold text-text-primary tracking-tight font-mono">
                      {String(distinctVaults)} / {String(totalGuesses)}
                    </span>
                    <Badge variant="outline" className="bg-purple-500/15 text-purple-300 border-purple-500/30 text-[11px] font-semibold">
                      100% Distinct
                    </Badge>
                  </div>
                  <p className="text-xs text-text-secondary mt-1">
                    {attack.conventional.cracked && guessIndex !== null && guessIndex !== undefined
                      ? `Baseline: Cracks at #${String(guessIndex)} of ${String(totalGuesses)}`
                      : `Baseline: Not cracked in ${String(totalGuesses)} guesses`}
                  </p>
                </div>
              )}

              {attack !== undefined && (
                <div className="pt-2.5 border-t border-border/60 flex items-center justify-between text-xs text-text-muted">
                  <span>Honey vaults:</span>
                  <span className="font-mono text-accent font-semibold">
                    {String(distinctVaults)} decoys (0 oracle)
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </TooltipProvider>
  );
}
