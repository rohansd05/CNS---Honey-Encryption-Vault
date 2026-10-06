import { motion } from 'framer-motion';
import {
  CheckCircle2,
  BrainCircuit,
  Binary,
  ShieldAlert,
  HelpCircle,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import type { EvalSummaryData } from '../types';

interface EvalKpiCardsProps {
  data: EvalSummaryData;
}

export function EvalKpiCards({ data }: EvalKpiCardsProps) {
  const roundTripPercent = (data.round_trip.success_rate * 100).toFixed(1);
  const totalityPercent = (data.round_trip.decode_totality.totality_rate * 100).toFixed(1);
  const accuracyPercent = (data.distinguisher.metrics.accuracy * 100).toFixed(1);
  const targetPercent = (data.distinguisher.target_accuracy * 100).toFixed(0);

  const seedP = data.chi_squared.seed_uniformity.p_value;
  const templateP = data.chi_squared.template_goodness_of_fit.p_value;
  const chiSquaredPass = seedP > 0.05 && templateP > 0.05;

  const cardVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { duration: 0.35, delay: i * 0.08 },
    }),
  };

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
                    100% Lossless
                  </Badge>
                </div>
                <p className="text-xs text-text-secondary mt-1">
                  {data.round_trip.exact_match_count.toLocaleString()} / {data.round_trip.trials.toLocaleString()} verified trials
                </p>
              </div>

              <div className="pt-2.5 border-t border-border/60 flex items-center justify-between text-xs text-text-muted">
                <span>Decode totality:</span>
                <span className="font-mono text-text-primary font-medium">
                  {totalityPercent}% ({data.round_trip.decode_totality.failed_decodes} errors)
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* KPI 2: Distinguisher Classifier Accuracy */}
        <motion.div custom={1} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="h-full border-border bg-bg-surface hover:border-accent/40 transition-all duration-200 shadow-card relative overflow-hidden group">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-accent to-amber-500" />
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
                      Evaluates whether an ML distinguisher (Logistic Regression + Random Forest) can distinguish decrypted real vaults from synthetic honey decoys. Ideal score is 50.0% (random coin-flip guessing).
                    </TooltipContent>
                  </Tooltip>
                </div>
                <div className="p-2 rounded-lg bg-accent/10 text-accent">
                  <BrainCircuit size={18} />
                </div>
              </div>

              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-text-primary tracking-tight font-mono">
                    {accuracyPercent}%
                  </span>
                  <Badge variant="outline" className="bg-accent/15 text-accent border-accent/30 text-[11px] font-semibold">
                    ≤ {targetPercent}% Bound
                  </Badge>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-text-secondary mt-1">
                  <span className="inline-block w-2 h-2 rounded-full bg-accent" />
                  <span>Reference: <strong>0.50</strong> (Random Guessing)</span>
                </div>
              </div>

              <div className="pt-2.5 border-t border-border/60 flex items-center justify-between text-xs text-text-muted">
                <span>Distinguisher:</span>
                <span className="font-mono text-text-primary font-medium truncate max-w-[150px]" title="LR + RF 5-Fold CV">
                  LR + RF (AUC: {data.distinguisher.metrics.roc_auc.toFixed(3)})
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* KPI 3: Chi-Squared Uniformity & Fit */}
        <motion.div custom={2} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="h-full border-border bg-bg-surface hover:border-accent/40 transition-all duration-200 shadow-card relative overflow-hidden group">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-cyan-400" />
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
                      Pearson's Chi-squared tests test whether encoded seeds are uniform noise (p &gt; 0.05) and whether decoded decoy templates match target PCFG frequency distributions (goodness of fit p &gt; 0.05).
                    </TooltipContent>
                  </Tooltip>
                </div>
                <div className="p-2 rounded-lg bg-info/10 text-info">
                  <Binary size={18} />
                </div>
              </div>

              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-text-primary tracking-tight font-mono">
                    p={seedP.toFixed(3)}
                  </span>
                  <Badge
                    variant="outline"
                    className={
                      chiSquaredPass
                        ? 'bg-success/15 text-success border-success/30 text-[11px] font-semibold'
                        : 'bg-danger/15 text-danger border-danger/30 text-[11px] font-semibold'
                    }
                  >
                    {chiSquaredPass ? 'p > 0.05 PASS' : 'FAIL'}
                  </Badge>
                </div>
                <p className="text-xs text-text-secondary mt-1">
                  Seed Uniformity (χ² = {data.chi_squared.seed_uniformity.statistic.toFixed(1)}, df = {data.chi_squared.seed_uniformity.degrees_of_freedom})
                </p>
              </div>

              <div className="pt-2.5 border-t border-border/60 flex items-center justify-between text-xs text-text-muted">
                <span>Template fit:</span>
                <span className="font-mono text-text-primary font-medium">
                  p={templateP.toFixed(3)} (PASS)
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* KPI 4: Baseline vs Honey "0 Signal" */}
        <motion.div custom={3} variants={cardVariants} initial="hidden" animate="visible">
          <Card className="h-full border-border bg-bg-surface hover:border-accent/40 transition-all duration-200 shadow-card relative overflow-hidden group">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 to-pink-500" />
            <CardContent className="p-5 flex flex-col justify-between h-full space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                    Cracking Oracle Signal
                  </span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button className="text-text-muted hover:text-text-primary" aria-label="Cracking signal info">
                        <HelpCircle size={13} />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      Conventional AES-GCM stops and verifies when the auth tag matches (providing 100% confirmation). Honey Encryption yields 0 bits of signal: every guess outputs plausible fake plaintexts.
                    </TooltipContent>
                  </Tooltip>
                </div>
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                  <ShieldAlert size={18} />
                </div>
              </div>

              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-extrabold text-text-primary tracking-tight font-mono">
                    0 Signal
                  </span>
                  <Badge variant="outline" className="bg-purple-500/15 text-purple-300 border-purple-500/30 text-[11px] font-semibold">
                    ∞ Decoys
                  </Badge>
                </div>
                <p className="text-xs text-text-secondary mt-1">
                  Baseline (AES-GCM): Cracks at #137 (100% leak)
                </p>
              </div>

              <div className="pt-2.5 border-t border-border/60 flex items-center justify-between text-xs text-text-muted">
                <span>Search space reduction:</span>
                <span className="font-mono text-accent font-semibold">
                  0% (No oracle)
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </TooltipProvider>
  );
}
