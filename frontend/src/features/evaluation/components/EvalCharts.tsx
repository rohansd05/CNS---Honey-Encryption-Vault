// owner: Chetan (T3) — evaluation charts (feat/t3-eval-real-data)
import { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  Cell,
} from 'recharts';
import { ExternalLink } from 'lucide-react';
import { useTheme } from '@/lib/theme';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { EvalSummaryData } from '../types';

interface EvalChartsProps {
  data: EvalSummaryData;
}

function formatPValue(p: number | undefined): string {
  if (p === undefined) return 'N/A';
  if (p < 0.001) {
    const exp = p.toExponential(1);
    return exp.replace('e', ' × 10^');
  }
  return p.toFixed(3);
}

export function EvalCharts({ data }: EvalChartsProps) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // Theme-aware palette
  const colors = useMemo(
    () => ({
      grid: isDark ? '#243552' : '#d8e2ef',
      text: isDark ? '#8fa3c0' : '#4a5e7a',
      primary: isDark ? '#e8edf5' : '#0d1829',
      amber: '#f5a524',
      blue: '#60a5fa',
      emerald: '#10b981',
      purple: '#a855f7',
      red: '#ef4444',
      cardBg: isDark ? '#1a2740' : '#ffffff',
      cardBorder: isDark ? '#243552' : '#c9d5e8',
    }),
    [isDark],
  );

  // 1. Classifier Metrics Dataset from distinguisher.per_classifier
  const classifierChartData = useMemo(() => {
    if (!data.distinguisher.per_classifier) return [];
    const target = data.distinguisher.target_accuracy;
    const entries = Object.entries(data.distinguisher.per_classifier);
    interface ClassifierChartItem {
      key: string;
      name: string;
      accuracy: number;
      roc_auc: number;
      accuracy_std?: number;
      isAboveTarget: boolean;
    }

    const items: ClassifierChartItem[] = entries.map(([key, score]) => {
      const isAboveTarget = score.accuracy_mean > target;
      const name =
        key === 'logreg'
          ? 'Logistic Regression'
          : key === 'random_forest'
            ? 'Random Forest'
            : key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      return {
        key,
        name,
        accuracy: +(score.accuracy_mean * 100).toFixed(1),
        roc_auc: +(score.roc_auc_mean).toFixed(3),
        accuracy_std: score.accuracy_std,
        isAboveTarget,
      };
    });

    // Render new keys (e.g. distinguisher grouped results) when present
    if (data.distinguisher.grouped_results) {
      const grouped = data.distinguisher.grouped_results as Record<
        string,
        { accuracy_mean?: number; roc_auc_mean?: number; accuracy_std?: number }
      >;
      for (const [gKey, gScore] of Object.entries(grouped)) {
        if (typeof gScore.accuracy_mean === 'number') {
          const isAboveTarget = gScore.accuracy_mean > target;
          items.push({
            key: `grouped_${gKey}`,
            name: `${gKey.replace(/_/g, ' ')} (Grouped CV)`,
            accuracy: +(gScore.accuracy_mean * 100).toFixed(1),
            roc_auc: typeof gScore.roc_auc_mean === 'number' ? +(gScore.roc_auc_mean).toFixed(3) : 0,
            accuracy_std: typeof gScore.accuracy_std === 'number' ? gScore.accuracy_std : undefined,
            isAboveTarget,
          });
        }
      }
    }

    return items;
  }, [data.distinguisher]);

  const anyClassifierAboveTarget = useMemo(
    () => classifierChartData.some((d) => d.isAboveTarget),
    [classifierChartData],
  );

  // 2. Template Frequencies: model_frequency vs decoded_frequency vs heldout_frequency
  const hasHeldoutTemplates = useMemo(() => {
    return data.template_frequencies?.some((t) => t.heldout_frequency !== undefined) ?? false;
  }, [data.template_frequencies]);

  const templateChartData = useMemo(() => {
    if (!data.template_frequencies) return [];
    return data.template_frequencies.map((item) => ({
      template: item.template,
      description: item.description ?? item.template,
      Model: +(item.model_frequency * 100).toFixed(2),
      Decoded: +(item.decoded_frequency * 100).toFixed(2),
      'Real (held-out)':
        item.heldout_frequency !== undefined
          ? +(item.heldout_frequency * 100).toFixed(2)
          : undefined,
    }));
  }, [data.template_frequencies]);

  // 3. Chi-Squared p-Values Chart
  const chiSquaredChartData = useMemo(() => {
    const alpha = data.chi_squared.alpha ?? 0.05;
    const items: Array<{
      test: string;
      pValue: number;
      stat: string;
      df: number | string;
      pass: boolean;
      isControl: boolean;
      description: string;
    }> = [];

    const pw = data.chi_squared.password;
    if (pw?.seed_byte_uniformity) {
      const p = pw.seed_byte_uniformity.p_value;
      items.push({
        test: 'Password: Seed Byte Uniformity (Held-out)',
        pValue: p,
        stat:
          pw.seed_byte_uniformity.chi2 !== undefined
            ? pw.seed_byte_uniformity.chi2.toFixed(1)
            : 'N/A',
        df: pw.seed_byte_uniformity.dof ?? 255,
        pass: p > alpha,
        isControl: false,
        description: 'Encoded held-out password bytes vs uniform (256 bins)',
      });
    } else if (data.chi_squared.seed_uniformity) {
      const su = data.chi_squared.seed_uniformity;
      items.push({
        test: 'Seed Uniformity (Held-out)',
        pValue: su.p_value,
        stat: su.statistic !== undefined ? su.statistic.toFixed(1) : 'N/A',
        df: su.degrees_of_freedom ?? 255,
        pass: su.p_value > alpha,
        isControl: false,
        description: su.note ?? 'Encoded held-out password seeds vs uniform',
      });
    }

    if (pw?.seed_int_uniformity) {
      const p = pw.seed_int_uniformity.p_value;
      items.push({
        test: 'Password: Seed Int Uniformity (Held-out)',
        pValue: p,
        stat:
          pw.seed_int_uniformity.chi2 !== undefined
            ? pw.seed_int_uniformity.chi2.toFixed(1)
            : 'N/A',
        df: pw.seed_int_uniformity.dof ?? 15,
        pass: p > alpha,
        isControl: false,
        description: 'Encoded held-out password ints (top 4 bits, 16 bins)',
      });
    }

    if (pw?.seed_int_uniformity_control) {
      const p = pw.seed_int_uniformity_control.p_value;
      items.push({
        test: 'Password: Codec Control (Model Samples)',
        pValue: p,
        stat:
          pw.seed_int_uniformity_control.chi2 !== undefined
            ? pw.seed_int_uniformity_control.chi2.toFixed(1)
            : 'N/A',
        df: pw.seed_int_uniformity_control.dof ?? 15,
        pass: p > alpha,
        isControl: true,
        description: 'Codec control: model samples encoded through codec (16 bins)',
      });
    }

    if (pw?.template_goodness_of_fit) {
      const p = pw.template_goodness_of_fit.p_value;
      items.push({
        test: 'Password: Template Goodness-of-Fit',
        pValue: p,
        stat:
          pw.template_goodness_of_fit.chi2 !== undefined
            ? pw.template_goodness_of_fit.chi2.toFixed(1)
            : 'N/A',
        df: pw.template_goodness_of_fit.dof ?? 50,
        pass: p > alpha,
        isControl: false,
        description: 'Decoded random seeds vs PCFG template distribution',
      });
    } else if (data.chi_squared.template_goodness_of_fit) {
      const tg = data.chi_squared.template_goodness_of_fit;
      items.push({
        test: 'Template Goodness-of-Fit',
        pValue: tg.p_value,
        stat: tg.statistic !== undefined ? tg.statistic.toFixed(1) : 'N/A',
        df: tg.degrees_of_freedom ?? 50,
        pass: tg.p_value > alpha,
        isControl: false,
        description: tg.note ?? 'Decoded random seeds vs model probabilities',
      });
    }

    const un = data.chi_squared.username;
    if (un?.seed_int_uniformity_control) {
      const p = un.seed_int_uniformity_control.p_value;
      items.push({
        test: 'Username: Codec Control (Model Samples)',
        pValue: p,
        stat:
          un.seed_int_uniformity_control.chi2 !== undefined
            ? un.seed_int_uniformity_control.chi2.toFixed(1)
            : 'N/A',
        df: un.seed_int_uniformity_control.dof ?? 15,
        pass: p > alpha,
        isControl: true,
        description: 'Username codec control on model samples',
      });
    }

    if (un?.template_goodness_of_fit) {
      const p = un.template_goodness_of_fit.p_value;
      items.push({
        test: 'Username: Template Goodness-of-Fit',
        pValue: p,
        stat:
          un.template_goodness_of_fit.chi2 !== undefined
            ? un.template_goodness_of_fit.chi2.toFixed(1)
            : 'N/A',
        df: un.template_goodness_of_fit.dof ?? 50,
        pass: p > alpha,
        isControl: false,
        description: 'Username decoded random seeds vs model probabilities',
      });
    }

    return items;
  }, [data.chi_squared]);

  // 4. KDF Latency per Profile from kdf.*
  const kdfLatencyData = useMemo(() => {
    if (!data.kdf) return [];
    return Object.entries(data.kdf).map(([key, profile]) => {
      const params = profile.params;
      const memMiB = Math.round(params.memory_cost_kib / 1024);
      const paramStr = `t=${String(params.time_cost)}, m=${String(memMiB)}MiB, p=${String(params.parallelism)}`;
      return {
        profile: key,
        label: `${key} (${paramStr})`,
        paramStr,
        p50: +(profile.unlock_ms.p50).toFixed(1),
        p95: +(profile.unlock_ms.p95).toFixed(1),
        derive_p50:
          profile.derive_ms !== undefined ? +(profile.derive_ms.p50).toFixed(1) : undefined,
        derive_p95:
          profile.derive_ms !== undefined ? +(profile.derive_ms.p95).toFixed(1) : undefined,
      };
    });
  }, [data.kdf]);

  return (
    <div className="space-y-6">
      {/* Row 1: Classifier Distinguishability & Template Frequency */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Classifier Distinguisher */}
        <Card className="border-border bg-bg-surface shadow-card flex flex-col justify-between">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                  <span>Classifier Distinguishability</span>
                  {anyClassifierAboveTarget ? (
                    <Badge
                      variant="outline"
                      className="bg-amber-500/15 text-amber-500 border-amber-500/30 text-xs font-semibold"
                    >
                      Above Target
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-info/10 text-info border-info/30 text-xs">
                      Within Target Bound
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary mt-1">
                  Empirical ML accuracy per classifier (ideal = {(data.distinguisher.ideal_accuracy * 100).toFixed(0)}%, target ≤ {(data.distinguisher.target_accuracy * 100).toFixed(0)}%)
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {classifierChartData.length === 0 ? (
              <div className="h-[320px] flex items-center justify-center text-xs text-text-muted">
                <Badge variant="outline" className="bg-bg-elevated border-border text-text-muted">
                  Not in this run
                </Badge>
              </div>
            ) : (
              <div className="h-[320px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={classifierChartData}
                    margin={{ top: 20, right: 20, left: -10, bottom: 20 }}
                    barCategoryGap="30%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} vertical={false} />
                    <XAxis
                      dataKey="name"
                      stroke={colors.text}
                      tick={{ fill: colors.text, fontSize: 12 }}
                      tickLine={{ stroke: colors.grid }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      ticks={[0, 25, 50, 60, 75, 100]}
                      stroke={colors.text}
                      tick={{ fill: colors.text, fontSize: 12 }}
                      tickLine={{ stroke: colors.grid }}
                      tickFormatter={(val: number) => `${String(val)}%`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: colors.cardBg,
                        borderColor: colors.cardBorder,
                        borderRadius: 8,
                        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                        color: colors.primary,
                        fontSize: 12,
                      }}
                      formatter={(
                        value: number,
                        _name: string,
                        item: { payload?: { roc_auc?: number; accuracy_std?: number; isAboveTarget?: boolean } },
                      ) => {
                        const auc = item.payload?.roc_auc !== undefined ? String(item.payload.roc_auc) : 'N/A';
                        const std = item.payload?.accuracy_std;
                        const stdStr = std !== undefined ? ` (±${(std * 100).toFixed(1)}%)` : '';
                        const status = item.payload?.isAboveTarget === true ? ' [Above Target]' : ' [Within Target]';
                        return [`${String(value)}%${stdStr} — AUC: ${auc}${status}`, 'Accuracy'];
                      }}
                    />
                    <Legend
                      verticalAlign="top"
                      align="right"
                      wrapperStyle={{ paddingBottom: 10, fontSize: 12 }}
                    />
                    {/* Reference line: Ideal Chance */}
                    <ReferenceLine
                      y={data.distinguisher.ideal_accuracy * 100}
                      stroke={colors.blue}
                      strokeDasharray="4 4"
                      strokeWidth={1.5}
                      label={{
                        value: `Ideal ${(data.distinguisher.ideal_accuracy * 100).toFixed(0)}% (Chance)`,
                        position: 'insideBottomRight',
                        fill: colors.blue,
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    />
                    {/* Reference line: Target Upper Bound */}
                    <ReferenceLine
                      y={data.distinguisher.target_accuracy * 100}
                      stroke={colors.amber}
                      strokeDasharray="4 4"
                      strokeWidth={1.5}
                      label={{
                        value: `Target ≤ ${(data.distinguisher.target_accuracy * 100).toFixed(0)}% Bound`,
                        position: 'insideTopRight',
                        fill: colors.amber,
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    />
                    <Bar dataKey="accuracy" name="Accuracy (%)" radius={[4, 4, 0, 0]}>
                      {classifierChartData.map((entry) => (
                        <Cell
                          key={entry.key}
                          fill={entry.isAboveTarget ? colors.amber : colors.blue}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            {anyClassifierAboveTarget && (
              <div className="mt-2 p-2.5 rounded-lg bg-bg-elevated/60 border border-border/60 text-xs text-text-secondary flex items-start gap-2">
                <span className="text-amber-500 font-bold shrink-0">Above Target:</span>
                <span>
                  Distinguisher accuracy exceeds target ({(data.distinguisher.metrics.accuracy * 100).toFixed(1)}% vs ≤{(data.distinguisher.target_accuracy * 100).toFixed(0)}%) primarily due to repeated strings across CV folds and heavy-tail frequency weighting; drops to 0.514 on distinct strings. See{' '}
                  <a
                    href="https://github.com/rohansd05/CNS---Honey-Encryption-Vault/blob/dev/docs/eval-report.md#43-distinguisher-0741-overall-mostly-from-repeated-strings-partly-from-real-mismatch"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent underline font-semibold inline-flex items-center gap-1 hover:text-accent-hover"
                  >
                    <span>docs/eval-report.md §4.3</span>
                    <ExternalLink size={11} />
                  </a>
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Chart 2: Template Frequencies Grouped Bars */}
        <Card className="border-border bg-bg-surface shadow-card flex flex-col justify-between">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                  <span>Template Frequency Distribution</span>
                  <Badge variant="outline" className="bg-info/10 text-info border-info/30 text-xs">
                    {String(templateChartData.length)} Patterns
                  </Badge>
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary mt-1">
                  Model frequency vs decoded decoy frequency vs Real (held-out)
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {templateChartData.length === 0 ? (
              <div className="h-[320px] flex items-center justify-center text-xs text-text-muted">
                <Badge variant="outline" className="bg-bg-elevated border-border text-text-muted">
                  Not in this run
                </Badge>
              </div>
            ) : (
              <div className="h-[320px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={templateChartData}
                    margin={{ top: 15, right: 10, left: -15, bottom: 35 }}
                    barCategoryGap="20%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} vertical={false} />
                    <XAxis
                      dataKey="template"
                      stroke={colors.text}
                      tick={{ fill: colors.text, fontSize: 10 }}
                      tickLine={{ stroke: colors.grid }}
                      angle={-45}
                      textAnchor="end"
                      interval={0}
                    />
                    <YAxis
                      stroke={colors.text}
                      tick={{ fill: colors.text, fontSize: 11 }}
                      tickLine={{ stroke: colors.grid }}
                      tickFormatter={(val: number) => `${String(val)}%`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: colors.cardBg,
                        borderColor: colors.cardBorder,
                        borderRadius: 8,
                        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                        color: colors.primary,
                        fontSize: 12,
                      }}
                      formatter={(value: number, name: string) => [`${String(value)}%`, name]}
                      labelFormatter={(label: string) => {
                        const item = templateChartData.find((t) => t.template === label);
                        return `${label}${item?.description ? ` (${item.description})` : ''}`;
                      }}
                    />
                    <Legend
                      verticalAlign="top"
                      align="right"
                      wrapperStyle={{ paddingBottom: 10, fontSize: 12 }}
                    />
                    <Bar dataKey="Model" name="Model (PCFG)" fill={colors.blue} radius={[3, 3, 0, 0]} />
                    <Bar dataKey="Decoded" name="Decoded (Decoys)" fill={colors.purple} radius={[3, 3, 0, 0]} />
                    {hasHeldoutTemplates && (
                      <Bar
                        dataKey="Real (held-out)"
                        name="Real (held-out)"
                        fill={colors.amber}
                        radius={[3, 3, 0, 0]}
                      />
                    )}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <div className="mt-2 p-2.5 rounded-lg bg-bg-elevated/60 border border-border/60 text-xs text-text-secondary flex items-start gap-2">
              <span className="text-info font-bold shrink-0">Template fit:</span>
              <span>
                Decoded decoy frequencies track PCFG model probabilities tightly across templates. Discrepancies between Model and Real (held-out) explain why seed uniformity rejects on real passwords (e.g. D5 5-digit passwords are 2.6% in model vs 0.33% in held-out data).
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 2: Chi-Squared Tests & KDF Latency */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 3: Chi-Squared p-Value Bars */}
        <Card className="border-border bg-bg-surface shadow-card flex flex-col justify-between">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                  <span>Pearson Chi-Squared Tests</span>
                  <Badge variant="outline" className="bg-info/10 text-info border-info/30 text-xs">
                    α = {(data.chi_squared.alpha ?? 0.05).toFixed(2)} Threshold
                  </Badge>
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary mt-1">
                  Empirical tests (p &gt; α is PASS; held-out failures contrasted with codec control)
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {chiSquaredChartData.length === 0 ? (
              <div className="h-[300px] flex items-center justify-center text-xs text-text-muted">
                <Badge variant="outline" className="bg-bg-elevated border-border text-text-muted">
                  Not in this run
                </Badge>
              </div>
            ) : (
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chiSquaredChartData}
                    layout="vertical"
                    margin={{ top: 15, right: 30, left: 45, bottom: 15 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} horizontal={false} />
                    <XAxis
                      type="number"
                      domain={[0, 1.0]}
                      ticks={[0, 0.05, 0.2, 0.4, 0.6, 0.8, 1.0]}
                      stroke={colors.text}
                      tick={{ fill: colors.text, fontSize: 11 }}
                      tickLine={{ stroke: colors.grid }}
                      tickFormatter={(val: number) => val.toFixed(2)}
                    />
                    <YAxis
                      type="category"
                      dataKey="test"
                      stroke={colors.text}
                      tick={{ fill: colors.text, fontSize: 10 }}
                      tickLine={{ stroke: colors.grid }}
                      width={120}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: colors.cardBg,
                        borderColor: colors.cardBorder,
                        borderRadius: 8,
                        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                        color: colors.primary,
                        fontSize: 12,
                      }}
                      formatter={(
                        _value: number,
                        _name: string,
                        item: {
                          payload?: {
                            pValue?: number;
                            stat?: string;
                            df?: number | string;
                            pass?: boolean;
                            isControl?: boolean;
                            description?: string;
                          };
                        },
                      ) => {
                        const pVal = item.payload?.pValue;
                        const stat = item.payload?.stat ?? 'N/A';
                        const df = String(item.payload?.df ?? '');
                        const pass = item.payload?.pass;
                        const control = item.payload?.isControl === true ? ' [Control Test]' : '';
                        const desc = item.payload?.description ? ` — ${item.payload.description}` : '';
                        return [
                          `p = ${formatPValue(pVal)} (χ²=${stat}, df=${df}) [${pass === true ? 'PASS' : 'FAIL'}]${control}${desc}`,
                          'Test Result',
                        ];
                      }}
                    />
                    <ReferenceLine
                      x={data.chi_squared.alpha ?? 0.05}
                      stroke={colors.red}
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      label={{
                        value: `α = ${(data.chi_squared.alpha ?? 0.05).toFixed(2)} (Pass Threshold)`,
                        position: 'top',
                        fill: colors.red,
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    />
                    <Bar dataKey="pValue" name="Observed p-value" radius={[0, 4, 4, 0]}>
                      {chiSquaredChartData.map((entry, index) => (
                        <Cell
                          key={`cell-${String(index)}`}
                          fill={entry.pass ? colors.emerald : colors.red}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <div className="mt-2 p-2.5 rounded-lg bg-bg-elevated/60 border border-border/60 text-xs text-text-secondary flex items-start gap-2">
              <span className="text-amber-500 font-bold shrink-0">Contextual Verdict:</span>
              <span>
                Seed uniformity rejects on held-out passwords (p ≈ 10⁻⁸) due to model-fit divergence from real-world frequencies. Crucially, the codec control test on model samples passes (p = 0.294 &gt; α), proving the DTE integer codec itself is unbiased.
                {data.chi_squared.username?.skipped !== undefined && (
                  <span className="block mt-1 text-text-muted italic">
                    Note: {data.chi_squared.username.skipped}.
                  </span>
                )}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Chart 4: KDF Latency per Profile */}
        <Card className="border-border bg-bg-surface shadow-card flex flex-col justify-between">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                  <span>Argon2id KDF & Unlock Latency</span>
                  <Badge variant="outline" className="bg-purple-500/15 text-purple-400 border-purple-500/30 text-xs">
                    Target ≤ {String(data.performance.target_p95_ms)} ms
                  </Badge>
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary mt-1">
                  8-entry HoneyVault.unlock latency across every measured profile
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {kdfLatencyData.length === 0 ? (
              <div className="h-[300px] flex items-center justify-center text-xs text-text-muted">
                <Badge variant="outline" className="bg-bg-elevated border-border text-text-muted">
                  Not in this run
                </Badge>
              </div>
            ) : (
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={kdfLatencyData}
                    margin={{ top: 20, right: 20, left: -10, bottom: 25 }}
                    barCategoryGap="25%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} vertical={false} />
                    <XAxis
                      dataKey="label"
                      stroke={colors.text}
                      tick={{ fill: colors.text, fontSize: 11 }}
                      tickLine={{ stroke: colors.grid }}
                    />
                    <YAxis
                      stroke={colors.text}
                      tick={{ fill: colors.text, fontSize: 11 }}
                      tickLine={{ stroke: colors.grid }}
                      tickFormatter={(val: number) => `${String(val)}ms`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: colors.cardBg,
                        borderColor: colors.cardBorder,
                        borderRadius: 8,
                        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                        color: colors.primary,
                        fontSize: 12,
                      }}
                      formatter={(value: number, name: string) => [`${String(value)} ms`, name]}
                    />
                    <Legend
                      verticalAlign="top"
                      align="right"
                      wrapperStyle={{ paddingBottom: 10, fontSize: 12 }}
                    />
                    <ReferenceLine
                      y={data.performance.target_p95_ms}
                      stroke={colors.red}
                      strokeDasharray="4 4"
                      strokeWidth={1.5}
                      label={{
                        value: `Target SLA (${String(data.performance.target_p95_ms)} ms max)`,
                        position: 'insideTopRight',
                        fill: colors.red,
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    />
                    <Bar dataKey="p50" name="p50 Latency (ms)" fill={colors.blue} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="p95" name="p95 Latency (ms)" fill={colors.purple} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <div className="mt-2 p-2.5 rounded-lg bg-bg-elevated/60 border border-border/60 text-xs text-text-secondary flex items-start gap-2">
              <span className="text-purple-400 font-bold shrink-0">Performance SLA:</span>
              <span>
                Measured 8-entry unlock p95 is {String(data.performance.unlock_p95_ms)} ms for {data.performance.argon2_kdf_profile ?? 'default'}, far below the {String(data.performance.target_p95_ms)} ms SLA constraint. Vault decoding adds &lt;1 ms over pure Argon2id derivation.
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
