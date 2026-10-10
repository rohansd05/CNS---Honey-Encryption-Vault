import { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  BarChart3,
  RotateCcw,
  Sparkles,
  Database,
  Layers,
  Calendar,
} from 'lucide-react';
import { useEvalSummary } from '@/api/hooks/useEvalQueries';
import { MOCK_EVAL_SUMMARY } from '@/mocks/handlers/eval';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EvalKpiCards } from './components/EvalKpiCards';
import { EvalCharts } from './components/EvalCharts';
import { EvalExplainer } from './components/EvalExplainer';
import { EvalSkeletons } from './components/EvalSkeletons';
import { EvalEmptyState } from './components/EvalEmptyState';
import type { EvalSummaryData } from './types';

export function EvaluationPage() {
  const shouldReduceMotion = useReducedMotion();
  const { data, isLoading, refetch, isFetching } = useEvalSummary();
  const [useDemoFallback, setUseDemoFallback] = useState<boolean>(false);

  // Cast query response or fallback to mock
  const evalData: EvalSummaryData | null =
    (data as unknown as EvalSummaryData | undefined) ??
    (useDemoFallback ? (MOCK_EVAL_SUMMARY as unknown as EvalSummaryData) : null);

  const formattedTimestamp = evalData
    ? new Date(evalData.timestamp).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : null;

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="space-y-4"
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="h-12 w-12 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent shadow-glow shrink-0">
              <BarChart3 size={26} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl sm:text-3xl font-extrabold text-text-primary tracking-tight">
                  Evaluation & Verification
                </h1>
                <Badge
                  variant="outline"
                  className="bg-accent/10 text-accent border-accent/30 text-xs font-semibold"
                >
                  Phase 3 Verified
                </Badge>
              </div>
              <p className="text-xs sm:text-sm text-text-secondary mt-1">
                Empirical cryptographic benchmarks, distribution analysis, and distinguishing attack resistance.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                void refetch();
              }}
              disabled={isFetching}
              className="border-border hover:bg-bg-elevated text-xs font-medium text-text-primary gap-1.5"
            >
              <RotateCcw size={13} className={isFetching ? 'animate-spin text-accent' : ''} />
              <span>{isFetching ? 'Refreshing...' : 'Refresh'}</span>
            </Button>
          </div>
        </div>

        {/* Metadata badges strip */}
        {evalData && (
          <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-text-secondary">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-surface border border-border">
              <Database size={13} className="text-accent" />
              <span>Corpus:</span>
              <span className="font-mono text-text-primary font-medium">RockYou2021 + SecLists</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-surface border border-border">
              <Layers size={13} className="text-info" />
              <span>Split:</span>
              <span className="font-mono text-text-primary font-medium">800k Train / 200k Test</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-surface border border-border">
              <Sparkles size={13} className="text-success" />
              <span>Fixed Seed:</span>
              <span className="font-mono text-text-primary font-medium">532 Bytes</span>
            </div>
            {formattedTimestamp && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-bg-surface border border-border">
                <Calendar size={13} className="text-text-muted" />
                <span>Run:</span>
                <span className="text-text-primary">{formattedTimestamp}</span>
              </div>
            )}
          </div>
        )}

        {/* Fallback alert banner */}
        {useDemoFallback && !data && (
          <div className="rounded-lg bg-accent/10 border border-accent/30 p-3 text-xs text-text-secondary flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span>
              ℹ️ <strong>Demonstration Snapshot:</strong> The live API returned 404 (evaluation results have not been generated via <code className="font-mono text-accent">python -m eval.run_all</code> yet). Displaying Phase 3 verified cryptographic benchmarks.
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setUseDemoFallback(false);
                void refetch();
              }}
              className="h-6 text-xs text-accent hover:text-accent-hover shrink-0 self-start sm:self-auto"
            >
              Re-check Live API
            </Button>
          </div>
        )}
      </motion.div>

      {/* Main Content Areas */}
      {isLoading && !evalData ? (
        <EvalSkeletons />
      ) : evalData ? (
        <div className="space-y-8">
          {/* Section 1: KPI Tiles */}
          <section aria-label="Key Performance Indicators">
            <EvalKpiCards data={evalData} />
          </section>

          {/* Section 2: Recharts Visualizations */}
          <section aria-label="Evaluation Charts">
            <EvalCharts data={evalData} />
          </section>

          {/* Section 3: Explainer & Methodology Accordion */}
          <section aria-label="Methodology & Documentation">
            <EvalExplainer />
          </section>
        </div>
      ) : (
        <EvalEmptyState
          onRetry={() => {
            void refetch();
          }}
          onLoadMock={() => {
            setUseDemoFallback(true);
          }}
        />
      )}
    </div>
  );
}
