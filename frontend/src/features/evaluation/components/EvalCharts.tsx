// owner: Chetan (T3) — evaluation charts (feat/t3-eval-v3-ui)
import { useState, useMemo } from 'react';
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
import {
  ExternalLink,
  Clock,
  Cpu,
  BrainCircuit,
  User,
  Binary,
  Layers,
  Sparkles,
} from 'lucide-react';
import { useTheme } from '@/lib/theme';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { EvalSummaryData, ClassifierScore, TimingProfileResult } from '../types';

interface EvalChartsProps {
  data: EvalSummaryData;
}

interface ProtocolComparisonItem {
  key: string;
  name: string;
  shortName: string;
  lrAccuracy: number;
  rfAccuracy: number;
  lrAuc: number;
  rfAuc: number;
  lrStd?: number;
  rfStd?: number;
  bestAccuracy: number;
  bestClassifier: 'Random Forest' | 'Logistic Regression';
  isAboveTarget: boolean;
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

function buildProtocolItems(
  official?: { logreg?: ClassifierScore; random_forest?: ClassifierScore },
  grouped?: { logreg?: ClassifierScore; random_forest?: ClassifierScore },
  distinct?: { logreg?: ClassifierScore; random_forest?: ClassifierScore },
  target = 0.6,
): ProtocolComparisonItem[] {
  const items: ProtocolComparisonItem[] = [];

  if (official?.logreg && official.random_forest) {
    const lrAcc = official.logreg.accuracy_mean * 100;
    const rfAcc = official.random_forest.accuracy_mean * 100;
    const bestAcc = Math.max(lrAcc, rfAcc);
    items.push({
      key: 'official',
      name: 'With Replacement (Official §11)',
      shortName: 'With Replacement',
      lrAccuracy: +lrAcc.toFixed(1),
      rfAccuracy: +rfAcc.toFixed(1),
      lrAuc: +official.logreg.roc_auc_mean.toFixed(3),
      rfAuc: +official.random_forest.roc_auc_mean.toFixed(3),
      lrStd: official.logreg.accuracy_std,
      rfStd: official.random_forest.accuracy_std,
      bestAccuracy: +bestAcc.toFixed(1),
      bestClassifier: rfAcc >= lrAcc ? 'Random Forest' : 'Logistic Regression',
      isAboveTarget: bestAcc / 100 > target,
    });
  }

  if (grouped?.logreg && grouped.random_forest) {
    const lrAcc = grouped.logreg.accuracy_mean * 100;
    const rfAcc = grouped.random_forest.accuracy_mean * 100;
    const bestAcc = Math.max(lrAcc, rfAcc);
    items.push({
      key: 'grouped',
      name: 'Grouped by String (Grouped CV)',
      shortName: 'Grouped CV',
      lrAccuracy: +lrAcc.toFixed(1),
      rfAccuracy: +rfAcc.toFixed(1),
      lrAuc: +grouped.logreg.roc_auc_mean.toFixed(3),
      rfAuc: +grouped.random_forest.roc_auc_mean.toFixed(3),
      lrStd: grouped.logreg.accuracy_std,
      rfStd: grouped.random_forest.accuracy_std,
      bestAccuracy: +bestAcc.toFixed(1),
      bestClassifier: rfAcc >= lrAcc ? 'Random Forest' : 'Logistic Regression',
      isAboveTarget: bestAcc / 100 > target,
    });
  }

  if (distinct?.logreg && distinct.random_forest) {
    const lrAcc = distinct.logreg.accuracy_mean * 100;
    const rfAcc = distinct.random_forest.accuracy_mean * 100;
    const bestAcc = Math.max(lrAcc, rfAcc);
    items.push({
      key: 'distinct',
      name: 'Distinct Strings Only',
      shortName: 'Distinct Strings',
      lrAccuracy: +lrAcc.toFixed(1),
      rfAccuracy: +rfAcc.toFixed(1),
      lrAuc: +distinct.logreg.roc_auc_mean.toFixed(3),
      rfAuc: +distinct.random_forest.roc_auc_mean.toFixed(3),
      lrStd: distinct.logreg.accuracy_std,
      rfStd: distinct.random_forest.accuracy_std,
      bestAccuracy: +bestAcc.toFixed(1),
      bestClassifier: rfAcc >= lrAcc ? 'Random Forest' : 'Logistic Regression',
      isAboveTarget: bestAcc / 100 > target,
    });
  }

  return items;
}

export function EvalCharts({ data }: EvalChartsProps) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [usernameTab, setUsernameTab] = useState<'as_stored' | 'without_domain'>('as_stored');

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

  const target = data.distinguisher.target_accuracy;
  const ideal = data.distinguisher.ideal_accuracy;

  // 1. Password Distinguisher Protocols (Official vs Grouped vs Distinct)
  const passwordProtocols = useMemo(() => {
    const official = {
      logreg: data.distinguisher.per_classifier?.logreg ?? data.classifier?.password?.logreg,
      random_forest:
        data.distinguisher.per_classifier?.random_forest ??
        data.classifier?.password?.random_forest,
    };
    const grouped = {
      logreg: data.distinguisher.grouped_results?.logreg ?? data.classifier?.password?.grouped?.logreg,
      random_forest:
        data.distinguisher.grouped_results?.random_forest ??
        data.classifier?.password?.grouped?.random_forest,
    };
    const distinct = {
      logreg: data.distinguisher.distinct_results?.logreg ?? data.classifier?.password?.distinct?.logreg,
      random_forest:
        data.distinguisher.distinct_results?.random_forest ??
        data.classifier?.password?.distinct?.random_forest,
    };

    return buildProtocolItems(official, grouped, distinct, target);
  }, [data.distinguisher, data.classifier, target]);

  const pwOfficialItem = passwordProtocols.find((p) => p.key === 'official');
  const pwGroupedItem = passwordProtocols.find((p) => p.key === 'grouped');
  const pwDistinctItem = passwordProtocols.find((p) => p.key === 'distinct');
  const anyPasswordAboveTarget = passwordProtocols.some((p) => p.isAboveTarget);

  // 2. Username Distinguisher Protocols (As Stored vs Without Domain)
  const usernameAsStoredProtocols = useMemo(() => {
    const un = data.classifier?.username;
    if (!un) return [];
    const official = { logreg: un.logreg, random_forest: un.random_forest };
    const grouped = un.grouped ? { logreg: un.grouped.logreg, random_forest: un.grouped.random_forest } : undefined;
    const distinct = un.distinct ? { logreg: un.distinct.logreg, random_forest: un.distinct.random_forest } : undefined;
    return buildProtocolItems(official, grouped, distinct, target);
  }, [data.classifier, target]);

  const usernameWithoutDomainProtocols = useMemo(() => {
    const wd = data.classifier?.username?.without_domain;
    if (!wd) return [];
    const official = { logreg: wd.logreg, random_forest: wd.random_forest };
    const grouped = wd.grouped ? { logreg: wd.grouped.logreg, random_forest: wd.grouped.random_forest } : undefined;
    const distinct = wd.distinct ? { logreg: wd.distinct.logreg, random_forest: wd.distinct.random_forest } : undefined;
    return buildProtocolItems(official, grouped, distinct, target);
  }, [data.classifier, target]);

  const hasUsernameDistinguisher = Boolean(data.classifier?.username);
  const hasWithoutDomain = Boolean(data.classifier?.username?.without_domain);
  const activeUsernameProtocols =
    usernameTab === 'as_stored' ? usernameAsStoredProtocols : usernameWithoutDomainProtocols;
  const anyUsernameAboveTarget = activeUsernameProtocols.some((p) => p.isAboveTarget);

  // 3. Template Frequencies: model_frequency vs decoded_frequency vs heldout_frequency
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

  const d5Item = data.template_frequencies?.find((t) => t.template === 'D5');
  const d5DynamicContext =
    d5Item && d5Item.heldout_frequency !== undefined
      ? ` (e.g. ${d5Item.template} 5-digit passwords are ${(d5Item.model_frequency * 100).toFixed(1)}% in model vs ${(d5Item.heldout_frequency * 100).toFixed(2)}% in held-out data)`
      : '';

  // 4. Chi-Squared p-Values Chart
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
        pValue: Math.max(p, 1e-300),
        stat:
          pw.seed_byte_uniformity.chi2 !== undefined
            ? pw.seed_byte_uniformity.chi2.toFixed(1)
            : 'N/A',
        df: pw.seed_byte_uniformity.dof ?? pw.seed_byte_uniformity.degrees_of_freedom ?? 255,
        pass: p > alpha,
        isControl: false,
        description: 'Encoded held-out password bytes vs uniform (256 bins)',
      });
    } else if (data.chi_squared.seed_uniformity) {
      const su = data.chi_squared.seed_uniformity;
      items.push({
        test: 'Seed Uniformity (Held-out)',
        pValue: Math.max(su.p_value, 1e-300),
        stat:
          su.statistic !== undefined
            ? su.statistic.toFixed(1)
            : su.chi2 !== undefined
              ? su.chi2.toFixed(1)
              : 'N/A',
        df: su.dof ?? su.degrees_of_freedom ?? 255,
        pass: su.p_value > alpha,
        isControl: false,
        description: su.note ?? 'Encoded held-out password seeds vs uniform',
      });
    }

    if (pw?.seed_int_uniformity) {
      const p = pw.seed_int_uniformity.p_value;
      items.push({
        test: 'Password: Seed Int Uniformity (Held-out)',
        pValue: Math.max(p, 1e-300),
        stat:
          pw.seed_int_uniformity.chi2 !== undefined
            ? pw.seed_int_uniformity.chi2.toFixed(1)
            : 'N/A',
        df: pw.seed_int_uniformity.dof ?? pw.seed_int_uniformity.degrees_of_freedom ?? 15,
        pass: p > alpha,
        isControl: false,
        description: 'Encoded held-out password ints (top 4 bits, 16 bins)',
      });
    }

    if (pw?.seed_int_uniformity_control) {
      const p = pw.seed_int_uniformity_control.p_value;
      items.push({
        test: 'Password: Codec Control (Model Samples)',
        pValue: Math.max(p, 1e-300),
        stat:
          pw.seed_int_uniformity_control.chi2 !== undefined
            ? pw.seed_int_uniformity_control.chi2.toFixed(1)
            : 'N/A',
        df: pw.seed_int_uniformity_control.dof ?? pw.seed_int_uniformity_control.degrees_of_freedom ?? 15,
        pass: p > alpha,
        isControl: true,
        description: 'Codec control: model samples encoded through codec (16 bins)',
      });
    }

    if (pw?.seed_pit_uniformity) {
      const p = pw.seed_pit_uniformity.p_value;
      items.push({
        test: 'Password: Seed PIT Uniformity (Held-out)',
        pValue: Math.max(p, 1e-300),
        stat:
          pw.seed_pit_uniformity.chi2 !== undefined
            ? pw.seed_pit_uniformity.chi2.toFixed(1)
            : 'N/A',
        df: pw.seed_pit_uniformity.dof ?? pw.seed_pit_uniformity.degrees_of_freedom ?? 15,
        pass: p > alpha,
        isControl: false,
        description:
          'Randomized PIT of every used seed int vs uniform (works for any distribution total)',
      });
    }

    if (pw?.seed_pit_uniformity_control) {
      const p = pw.seed_pit_uniformity_control.p_value;
      items.push({
        test: 'Password: PIT Codec Control (Model Samples)',
        pValue: Math.max(p, 1e-300),
        stat:
          pw.seed_pit_uniformity_control.chi2 !== undefined
            ? pw.seed_pit_uniformity_control.chi2.toFixed(1)
            : 'N/A',
        df:
          pw.seed_pit_uniformity_control.dof ??
          pw.seed_pit_uniformity_control.degrees_of_freedom ??
          15,
        pass: p > alpha,
        isControl: true,
        description:
          'Randomized PIT of every used seed int vs uniform (works for any distribution total)',
      });
    }

    if (pw?.template_goodness_of_fit) {
      const p = pw.template_goodness_of_fit.p_value;
      items.push({
        test: 'Password: Template Goodness-of-Fit',
        pValue: Math.max(p, 1e-300),
        stat:
          pw.template_goodness_of_fit.chi2 !== undefined
            ? pw.template_goodness_of_fit.chi2.toFixed(1)
            : 'N/A',
        df: pw.template_goodness_of_fit.dof ?? pw.template_goodness_of_fit.degrees_of_freedom ?? 50,
        pass: p > alpha,
        isControl: false,
        description: 'Decoded random seeds vs PCFG template distribution',
      });
    } else if (data.chi_squared.template_goodness_of_fit) {
      const tg = data.chi_squared.template_goodness_of_fit;
      items.push({
        test: 'Template Goodness-of-Fit',
        pValue: Math.max(tg.p_value, 1e-300),
        stat:
          tg.statistic !== undefined
            ? tg.statistic.toFixed(1)
            : tg.chi2 !== undefined
              ? tg.chi2.toFixed(1)
              : 'N/A',
        df: tg.dof ?? tg.degrees_of_freedom ?? 50,
        pass: tg.p_value > alpha,
        isControl: false,
        description: tg.note ?? 'Decoded random seeds vs model probabilities',
      });
    }

    const un = data.chi_squared.username;
    if (un?.seed_byte_uniformity) {
      const p = un.seed_byte_uniformity.p_value;
      items.push({
        test: 'Username: Seed Byte Uniformity (Held-out)',
        pValue: Math.max(p, 1e-300),
        stat:
          un.seed_byte_uniformity.chi2 !== undefined
            ? un.seed_byte_uniformity.chi2.toFixed(1)
            : 'N/A',
        df: un.seed_byte_uniformity.dof ?? un.seed_byte_uniformity.degrees_of_freedom ?? 255,
        pass: p > alpha,
        isControl: false,
        description: 'Encoded held-out username bytes vs uniform (256 bins)',
      });
    }

    if (un?.seed_int_uniformity) {
      const p = un.seed_int_uniformity.p_value;
      items.push({
        test: 'Username: Seed Int Uniformity (Held-out)',
        pValue: Math.max(p, 1e-300),
        stat:
          un.seed_int_uniformity.chi2 !== undefined
            ? un.seed_int_uniformity.chi2.toFixed(1)
            : 'N/A',
        df: un.seed_int_uniformity.dof ?? un.seed_int_uniformity.degrees_of_freedom ?? 15,
        pass: p > alpha,
        isControl: false,
        description: 'Encoded held-out username ints (top 4 bits, 16 bins)',
      });
    }

    if (un?.seed_int_uniformity_control) {
      const p = un.seed_int_uniformity_control.p_value;
      items.push({
        test: 'Username: Codec Control (Model Samples)',
        pValue: Math.max(p, 1e-300),
        stat:
          un.seed_int_uniformity_control.chi2 !== undefined
            ? un.seed_int_uniformity_control.chi2.toFixed(1)
            : 'N/A',
        df: un.seed_int_uniformity_control.dof ?? un.seed_int_uniformity_control.degrees_of_freedom ?? 15,
        pass: p > alpha,
        isControl: true,
        description: 'Username codec control on model samples',
      });
    }

    if (un?.seed_pit_uniformity) {
      const p = un.seed_pit_uniformity.p_value;
      items.push({
        test: 'Username: Seed PIT Uniformity (Held-out)',
        pValue: Math.max(p, 1e-300),
        stat:
          un.seed_pit_uniformity.chi2 !== undefined
            ? un.seed_pit_uniformity.chi2.toFixed(1)
            : 'N/A',
        df: un.seed_pit_uniformity.dof ?? un.seed_pit_uniformity.degrees_of_freedom ?? 15,
        pass: p > alpha,
        isControl: false,
        description:
          'Randomized PIT of every used seed int vs uniform (works for any distribution total)',
      });
    }

    if (un?.seed_pit_uniformity_control) {
      const p = un.seed_pit_uniformity_control.p_value;
      items.push({
        test: 'Username: PIT Codec Control (Model Samples)',
        pValue: Math.max(p, 1e-300),
        stat:
          un.seed_pit_uniformity_control.chi2 !== undefined
            ? un.seed_pit_uniformity_control.chi2.toFixed(1)
            : 'N/A',
        df:
          un.seed_pit_uniformity_control.dof ??
          un.seed_pit_uniformity_control.degrees_of_freedom ??
          15,
        pass: p > alpha,
        isControl: true,
        description:
          'Randomized PIT of every used seed int vs uniform (works for any distribution total)',
      });
    }

    if (un?.template_goodness_of_fit) {
      const p = un.template_goodness_of_fit.p_value;
      items.push({
        test: 'Username: Template Goodness-of-Fit',
        pValue: Math.max(p, 1e-300),
        stat:
          un.template_goodness_of_fit.chi2 !== undefined
            ? un.template_goodness_of_fit.chi2.toFixed(1)
            : 'N/A',
        df: un.template_goodness_of_fit.dof ?? un.template_goodness_of_fit.degrees_of_freedom ?? 50,
        pass: p > alpha,
        isControl: false,
        description: 'Username decoded random seeds vs model probabilities',
      });
    }

    return items;
  }, [data.chi_squared]);

  const pwSeedP =
    data.chi_squared.password?.seed_pit_uniformity?.p_value ??
    data.chi_squared.password?.seed_byte_uniformity?.p_value ??
    data.chi_squared.seed_uniformity?.p_value;
  const pwControlP =
    data.chi_squared.password?.seed_pit_uniformity_control?.p_value ??
    data.chi_squared.password?.seed_int_uniformity_control?.p_value;
  const unControlP =
    data.chi_squared.username?.seed_pit_uniformity_control?.p_value ??
    data.chi_squared.username?.seed_int_uniformity_control?.p_value;

  // 5. KDF Latency per Profile from kdf.*
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
        p50: +profile.unlock_ms.p50.toFixed(1),
        p95: +profile.unlock_ms.p95.toFixed(1),
        derive_p50:
          profile.derive_ms !== undefined ? +profile.derive_ms.p50.toFixed(1) : undefined,
        derive_p95:
          profile.derive_ms !== undefined ? +profile.derive_ms.p95.toFixed(1) : undefined,
      };
    });
  }, [data.kdf]);

  // 6. Timing Kolmogorov-Smirnov Test Data from timing.*
  const timingChartData = useMemo(() => {
    if (!data.timing?.profiles) return [];
    return Object.entries(data.timing.profiles)
      .filter((entry): entry is [string, TimingProfileResult] => Boolean(entry[1]))
      .map(([profileKey, prof]) => {
      const label =
        profileKey === 'default'
          ? 'default (64 MiB)'
          : profileKey === 'server_lite'
            ? 'server_lite (19 MiB)'
            : 'demo (8 MiB)';
      return {
        profile: profileKey,
        label,
        right_p50: +prof.right_ms.p50.toFixed(2),
        wrong_p50: +prof.wrong_ms.p50.toFixed(2),
        right_p95: +prof.right_ms.p95.toFixed(1),
        wrong_p95: +prof.wrong_ms.p95.toFixed(1),
        ks_statistic: +prof.ks_statistic.toFixed(3),
        ks_p_value: prof.ks_p_value,
        control_ks_p_value: prof.control_ks_p_value,
        same_distribution: prof.same_distribution,
      };
    });
  }, [data.timing]);

  const allTimingPass =
    timingChartData.length > 0 && timingChartData.every((p) => p.same_distribution);

  return (
    <div className="space-y-6">
      {/* Row 1: Distinguishers (Passwords & Usernames) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Card 1: Password Distinguisher */}
        <Card className="border-border bg-bg-surface shadow-card flex flex-col justify-between">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                  <BrainCircuit size={19} className="text-accent" />
                  <span>Password Distinguisher</span>
                  {anyPasswordAboveTarget ? (
                    <Badge
                      variant="outline"
                      className="bg-amber-500/15 text-amber-500 border-amber-500/30 text-xs font-semibold"
                    >
                      Official Above Target
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-info/10 text-info border-info/30 text-xs">
                      Within Target Bound
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary mt-1">
                  Current (with replacement) vs Grouped CV vs Distinct strings (LR and RF)
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {passwordProtocols.length === 0 ? (
              <div className="h-[320px] flex items-center justify-center text-xs text-text-muted">
                <Badge variant="outline" className="bg-bg-elevated border-border text-text-muted">
                  Not in this run
                </Badge>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Bar chart comparison */}
                <div className="h-[230px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={passwordProtocols}
                      margin={{ top: 15, right: 15, left: -15, bottom: 5 }}
                      barCategoryGap="25%"
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} vertical={false} />
                      <XAxis
                        dataKey="shortName"
                        stroke={colors.text}
                        tick={{ fill: colors.text, fontSize: 11 }}
                        tickLine={{ stroke: colors.grid }}
                      />
                      <YAxis
                        domain={[0, 100]}
                        ticks={[0, 25, 50, 60, 75, 100]}
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
                        formatter={(
                          value: number,
                          name: string,
                          item: { payload?: ProtocolComparisonItem },
                        ) => {
                          const isRf = name.includes('Random Forest');
                          const auc = isRf ? item.payload?.rfAuc : item.payload?.lrAuc;
                          const std = isRf ? item.payload?.rfStd : item.payload?.lrStd;
                          const stdStr = std !== undefined ? ` (±${(std * 100).toFixed(1)}%)` : '';
                          return [`${String(value)}%${stdStr} — AUC: ${String(auc)}`, name];
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        align="right"
                        wrapperStyle={{ paddingBottom: 6, fontSize: 11 }}
                      />
                      <ReferenceLine
                        y={ideal * 100}
                        stroke={colors.blue}
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                        label={{
                          value: `Ideal ${(ideal * 100).toFixed(0)}% (Chance)`,
                          position: 'insideBottomRight',
                          fill: colors.blue,
                          fontSize: 10,
                          fontWeight: 600,
                        }}
                      />
                      <ReferenceLine
                        y={target * 100}
                        stroke={colors.amber}
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                        label={{
                          value: `Target ≤ ${(target * 100).toFixed(0)}%`,
                          position: 'insideTopRight',
                          fill: colors.amber,
                          fontSize: 10,
                          fontWeight: 600,
                        }}
                      />
                      <Bar
                        dataKey="lrAccuracy"
                        name="Logistic Regression"
                        fill={colors.blue}
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar dataKey="rfAccuracy" name="Random Forest" radius={[4, 4, 0, 0]}>
                        {passwordProtocols.map((entry) => (
                          <Cell
                            key={entry.key}
                            fill={entry.rfAccuracy > target * 100 ? colors.amber : colors.purple}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Protocol comparison table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border border-border/70 rounded-lg overflow-hidden">
                    <thead className="bg-bg-elevated/70 text-text-secondary border-b border-border/70">
                      <tr>
                        <th className="py-1.5 px-2.5 font-semibold">Protocol</th>
                        <th className="py-1.5 px-2.5 font-semibold">LR (acc / AUC)</th>
                        <th className="py-1.5 px-2.5 font-semibold">RF (acc / AUC)</th>
                        <th className="py-1.5 px-2.5 font-semibold">Best</th>
                        <th className="py-1.5 px-2.5 font-semibold text-right">Verdict</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50 text-text-primary">
                      {passwordProtocols.map((row) => (
                        <tr key={row.key} className="hover:bg-bg-elevated/40 transition-colors">
                          <td className="py-1.5 px-2.5 font-medium">{row.name}</td>
                          <td className="py-1.5 px-2.5 font-mono">
                            {row.lrAccuracy}%{row.lrStd !== undefined ? ` (±${(row.lrStd * 100).toFixed(1)}%)` : ''} / {row.lrAuc}
                          </td>
                          <td className="py-1.5 px-2.5 font-mono">
                            {row.rfAccuracy}%{row.rfStd !== undefined ? ` (±${(row.rfStd * 100).toFixed(1)}%)` : ''} / {row.rfAuc}
                          </td>
                          <td className="py-1.5 px-2.5 font-semibold">
                            <span className={row.isAboveTarget ? 'text-amber-500' : 'text-emerald-500'}>
                              {row.bestAccuracy}% ({row.bestClassifier === 'Random Forest' ? 'RF' : 'LR'})
                            </span>
                          </td>
                          <td className="py-1.5 px-2.5 text-right font-medium">
                            {row.isAboveTarget ? (
                              <Badge
                                variant="outline"
                                className="bg-amber-500/15 text-amber-500 border-amber-500/30 text-[10px]"
                              >
                                Above Target
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className="bg-success/15 text-success border-success/30 text-[10px]"
                              >
                                Pass (≤{(target * 100).toFixed(0)}%)
                              </Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {pwOfficialItem && (
              <div className="mt-3 p-2.5 rounded-lg bg-bg-elevated/60 border border-border/60 text-xs text-text-secondary flex items-start gap-2">
                <span className="text-amber-500 font-bold shrink-0">Protocol Analysis:</span>
                <span>
                  Official with-replacement accuracy reaches {pwOfficialItem.rfAccuracy}% (RF) due to repeated strings across cross-validation folds.
                  {pwGroupedItem && (
                    <> In grouped CV, best accuracy drops to <strong>{pwGroupedItem.bestAccuracy}%</strong> ({pwGroupedItem.bestClassifier === 'Random Forest' ? 'RF' : 'LR'}).</>
                  )}
                  {pwDistinctItem && (
                    <> On distinct strings only, best accuracy falls to <strong>{pwDistinctItem.bestAccuracy}%</strong> ({pwDistinctItem.bestClassifier === 'Random Forest' ? 'RF' : 'LR'}), both within the ≤{(target * 100).toFixed(0)}% bound. See{' '}</>
                  )}
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

        {/* Card 2: Username Distinguisher */}
        <Card className="border-border bg-bg-surface shadow-card flex flex-col justify-between">
          <CardHeader className="pb-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <CardTitle className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                  <User size={19} className="text-accent" />
                  <span>Username Distinguisher</span>
                  {hasUsernameDistinguisher && (
                    <Badge
                      variant="outline"
                      className={
                        anyUsernameAboveTarget
                          ? 'bg-amber-500/15 text-amber-500 border-amber-500/30 text-xs font-semibold'
                          : 'bg-success/15 text-success border-success/30 text-xs font-semibold'
                      }
                    >
                      {anyUsernameAboveTarget ? 'Above Target' : 'Within Target Bound'}
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary mt-1">
                  Classifier performance on usernames as stored vs known email domain stripped
                </CardDescription>
              </div>

              {/* Sub-view switcher */}
              {hasUsernameDistinguisher && (
                <div className="flex items-center gap-1 p-0.5 rounded-lg bg-bg-elevated border border-border self-start sm:self-auto shrink-0">
                  <button
                    type="button"
                    onClick={() => {
                      setUsernameTab('as_stored');
                    }}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                      usernameTab === 'as_stored'
                        ? 'bg-accent text-bg font-semibold shadow-sm'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    As Stored
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setUsernameTab('without_domain');
                    }}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                      usernameTab === 'without_domain'
                        ? 'bg-accent text-bg font-semibold shadow-sm'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    Without Domain {hasWithoutDomain ? '' : '(absent)'}
                  </button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {!hasUsernameDistinguisher ? (
              <div className="h-[320px] flex flex-col items-center justify-center text-center p-6 space-y-2">
                <Badge variant="outline" className="bg-bg-elevated border-border text-text-muted text-xs">
                  Not in this run
                </Badge>
                <p className="text-xs text-text-secondary max-w-sm">
                  Username distinguisher evaluation was not included in this evaluation run.
                </p>
              </div>
            ) : usernameTab === 'without_domain' && !hasWithoutDomain ? (
              <div className="h-[320px] flex flex-col items-center justify-center text-center p-6 space-y-2">
                <Badge variant="outline" className="bg-bg-elevated border-border text-text-muted text-xs">
                  Not in this run
                </Badge>
                <p className="text-xs text-text-secondary max-w-sm">
                  Username evaluation without domain suffixes was not run or recorded in this summary file.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Bar chart comparison */}
                <div className="h-[230px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={activeUsernameProtocols}
                      margin={{ top: 15, right: 15, left: -15, bottom: 5 }}
                      barCategoryGap="25%"
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} vertical={false} />
                      <XAxis
                        dataKey="shortName"
                        stroke={colors.text}
                        tick={{ fill: colors.text, fontSize: 11 }}
                        tickLine={{ stroke: colors.grid }}
                      />
                      <YAxis
                        domain={[0, 100]}
                        ticks={[0, 25, 50, 60, 75, 100]}
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
                        formatter={(
                          value: number,
                          name: string,
                          item: { payload?: ProtocolComparisonItem },
                        ) => {
                          const isRf = name.includes('Random Forest');
                          const auc = isRf ? item.payload?.rfAuc : item.payload?.lrAuc;
                          const std = isRf ? item.payload?.rfStd : item.payload?.lrStd;
                          const stdStr = std !== undefined ? ` (±${(std * 100).toFixed(1)}%)` : '';
                          return [`${String(value)}%${stdStr} — AUC: ${String(auc)}`, name];
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        align="right"
                        wrapperStyle={{ paddingBottom: 6, fontSize: 11 }}
                      />
                      <ReferenceLine
                        y={ideal * 100}
                        stroke={colors.blue}
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                        label={{
                          value: `Ideal ${(ideal * 100).toFixed(0)}% (Chance)`,
                          position: 'insideBottomRight',
                          fill: colors.blue,
                          fontSize: 10,
                          fontWeight: 600,
                        }}
                      />
                      <ReferenceLine
                        y={target * 100}
                        stroke={colors.amber}
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                        label={{
                          value: `Target ≤ ${(target * 100).toFixed(0)}%`,
                          position: 'insideTopRight',
                          fill: colors.amber,
                          fontSize: 10,
                          fontWeight: 600,
                        }}
                      />
                      <Bar
                        dataKey="lrAccuracy"
                        name="Logistic Regression"
                        fill={colors.blue}
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar dataKey="rfAccuracy" name="Random Forest" radius={[4, 4, 0, 0]}>
                        {activeUsernameProtocols.map((entry) => (
                          <Cell
                            key={entry.key}
                            fill={entry.rfAccuracy > target * 100 ? colors.amber : colors.purple}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Protocol comparison table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border border-border/70 rounded-lg overflow-hidden">
                    <thead className="bg-bg-elevated/70 text-text-secondary border-b border-border/70">
                      <tr>
                        <th className="py-1.5 px-2.5 font-semibold">Protocol</th>
                        <th className="py-1.5 px-2.5 font-semibold">LR (acc / AUC)</th>
                        <th className="py-1.5 px-2.5 font-semibold">RF (acc / AUC)</th>
                        <th className="py-1.5 px-2.5 font-semibold">Best</th>
                        <th className="py-1.5 px-2.5 font-semibold text-right">Verdict</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50 text-text-primary">
                      {activeUsernameProtocols.map((row) => (
                        <tr key={row.key} className="hover:bg-bg-elevated/40 transition-colors">
                          <td className="py-1.5 px-2.5 font-medium">{row.name}</td>
                          <td className="py-1.5 px-2.5 font-mono">
                            {row.lrAccuracy}%{row.lrStd !== undefined ? ` (±${(row.lrStd * 100).toFixed(1)}%)` : ''} / {row.lrAuc}
                          </td>
                          <td className="py-1.5 px-2.5 font-mono">
                            {row.rfAccuracy}%{row.rfStd !== undefined ? ` (±${(row.rfStd * 100).toFixed(1)}%)` : ''} / {row.rfAuc}
                          </td>
                          <td className="py-1.5 px-2.5 font-semibold">
                            <span className={row.isAboveTarget ? 'text-amber-500' : 'text-emerald-500'}>
                              {row.bestAccuracy}% ({row.bestClassifier === 'Random Forest' ? 'RF' : 'LR'})
                            </span>
                          </td>
                          <td className="py-1.5 px-2.5 text-right font-medium">
                            {row.isAboveTarget ? (
                              <Badge
                                variant="outline"
                                className="bg-amber-500/15 text-amber-500 border-amber-500/30 text-[10px]"
                              >
                                Above Target
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className="bg-success/15 text-success border-success/30 text-[10px]"
                              >
                                Pass (≤{(target * 100).toFixed(0)}%)
                              </Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {hasUsernameDistinguisher && (
              <div className="mt-3 p-2.5 rounded-lg bg-bg-elevated/60 border border-border/60 text-xs text-text-secondary flex items-start gap-2">
                <span className="text-info font-bold shrink-0">
                  {usernameTab === 'as_stored' ? 'Email Suffix Leak:' : 'Domain-Stripped Analysis:'}
                </span>
                <span>
                  {usernameTab === 'as_stored' ? (
                    <>
                      As stored, real and decoy usernames separate across protocols because the username PCFG appends email domain suffixes from its table, while held-out usernames are bare strings. Both LR and RF detect this domain presence.
                    </>
                  ) : (
                    <>
                      {data.classifier?.username?.without_domain?.transformed?.decoy !== undefined && (
                        <span>
                          Stripped known domain from {data.classifier.username.without_domain.transformed.decoy.toLocaleString()} decoys:
                        </span>
                      )}{' '}
                      grouped CV and distinct accuracy fall within the ≤{(target * 100).toFixed(0)}% target bound, matching the password pattern. See{' '}
                    </>
                  )}
                  <a
                    href="https://github.com/rohansd05/CNS---Honey-Encryption-Vault/blob/dev/docs/eval-report.md#44-username-distinguisher-the-email-domain-suffix-gives-decoys-away"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent underline font-semibold inline-flex items-center gap-1 hover:text-accent-hover"
                  >
                    <span>docs/eval-report.md §4.4</span>
                    <ExternalLink size={11} />
                  </a>
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 2: Template Frequency Distribution & Chi-Squared Tests */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Card 3: Template Frequencies Grouped Bars */}
        <Card className="border-border bg-bg-surface shadow-card flex flex-col justify-between">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                  <Layers size={19} className="text-accent" />
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
                Decoded decoy frequencies track PCFG model probabilities tightly across templates. Discrepancies between Model and Real (held-out) explain why seed uniformity rejects on real passwords{d5DynamicContext}.
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Card 4: Chi-Squared p-Value Bars */}
        <Card className="border-border bg-bg-surface shadow-card flex flex-col justify-between">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                  <Binary size={19} className="text-accent" />
                  <span>Pearson Chi-Squared Tests</span>
                  <Badge variant="outline" className="bg-info/10 text-info border-info/30 text-xs">
                    α = {(data.chi_squared.alpha ?? 0.05).toFixed(2)} Threshold
                  </Badge>
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary mt-1">
                  Uniformity & goodness-of-fit (p &gt; α is PASS; held-out failures contrasted with codec control)
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
              <div className="h-[380px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chiSquaredChartData}
                    layout="vertical"
                    margin={{ top: 10, right: 30, left: 35, bottom: 10 }}
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
                      width={145}
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
                Seed uniformity rejects on held-out inputs ({pwSeedP !== undefined ? `password p = ${formatPValue(pwSeedP)}` : 'p < α'}) due to model-fit divergence from real-world frequencies. Crucially, the codec control test on model samples passes ({pwControlP !== undefined ? `p = ${formatPValue(pwControlP)} > α` : 'p > α'}{unControlP !== undefined ? `; username control p = ${formatPValue(unControlP)} > α` : ''}), proving the DTE integer codec itself is unbiased.
                {data.chi_squared.username?.skipped !== undefined && (
                  <span className="block mt-1 text-text-muted italic">
                    Note: {data.chi_squared.username.skipped}.
                  </span>
                )}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 3: Latency Hardening & Unlock Timing Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Card 5: KDF Latency per Profile */}
        <Card className="border-border bg-bg-surface shadow-card flex flex-col justify-between">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                  <Cpu size={19} className="text-accent" />
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

        {/* Card 6: Timing Kolmogorov-Smirnov Distribution */}
        <Card className="border-border bg-bg-surface shadow-card flex flex-col justify-between">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2">
                  <Clock size={19} className="text-accent" />
                  <span>Unlock Timing & KS Distribution</span>
                  {data.timing ? (
                    <Badge
                      variant="outline"
                      className={
                        allTimingPass
                          ? 'bg-success/15 text-success border-success/30 text-xs font-semibold'
                          : 'bg-amber-500/15 text-amber-500 border-amber-500/30 text-xs font-semibold'
                      }
                    >
                      {allTimingPass ? 'Pass (p > 0.05)' : 'Borderline Distribution'}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-bg-elevated border-border text-text-muted text-xs">
                      Not in this run
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription className="text-xs text-text-secondary mt-1">
                  Right vs wrong master password unlock latency (two-sample Kolmogorov-Smirnov test)
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            {!data.timing ? (
              <div className="h-[320px] flex flex-col items-center justify-center text-center p-6 space-y-2">
                <Badge variant="outline" className="bg-bg-elevated border-border text-text-muted text-xs">
                  Not in this run
                </Badge>
                <p className="text-xs text-text-secondary max-w-sm">
                  Interleaved unlock timing benchmarks and KS distribution tests were not recorded in this evaluation run.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Bar chart comparing Right vs Wrong unlock p50 */}
                <div className="h-[210px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={timingChartData}
                      margin={{ top: 15, right: 20, left: -10, bottom: 5 }}
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
                        formatter={(
                          value: number,
                          name: string,
                          item: {
                            payload?: {
                              right_p95?: number;
                              wrong_p95?: number;
                              ks_statistic?: number;
                              ks_p_value?: number;
                            };
                          },
                        ) => {
                          const isRight = name.includes('Right');
                          const p95 = isRight ? item.payload?.right_p95 : item.payload?.wrong_p95;
                          return [
                            `${String(value)} ms (p95: ${String(p95)} ms) — KS p: ${formatPValue(item.payload?.ks_p_value)}`,
                            name,
                          ];
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        align="right"
                        wrapperStyle={{ paddingBottom: 6, fontSize: 11 }}
                      />
                      <Bar
                        dataKey="right_p50"
                        name="Right Password (p50 ms)"
                        fill={colors.blue}
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        dataKey="wrong_p50"
                        name="Wrong Password (p50 ms)"
                        fill={colors.purple}
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Timing summary table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border border-border/70 rounded-lg overflow-hidden">
                    <thead className="bg-bg-elevated/70 text-text-secondary border-b border-border/70">
                      <tr>
                        <th className="py-1.5 px-2.5 font-semibold">Profile</th>
                        <th className="py-1.5 px-2.5 font-semibold">Right p50 / p95</th>
                        <th className="py-1.5 px-2.5 font-semibold">Wrong p50 / p95</th>
                        <th className="py-1.5 px-2.5 font-semibold">KS p (D)</th>
                        <th className="py-1.5 px-2.5 font-semibold text-right">Verdict</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50 text-text-primary">
                      {timingChartData.map((row) => (
                        <tr key={row.profile} className="hover:bg-bg-elevated/40 transition-colors">
                          <td className="py-1.5 px-2.5 font-medium">{row.label}</td>
                          <td className="py-1.5 px-2.5 font-mono">
                            {row.right_p50} / {row.right_p95} ms
                          </td>
                          <td className="py-1.5 px-2.5 font-mono">
                            {row.wrong_p50} / {row.wrong_p95} ms
                          </td>
                          <td className="py-1.5 px-2.5 font-mono">
                            p={formatPValue(row.ks_p_value)} (D={row.ks_statistic})
                          </td>
                          <td className="py-1.5 px-2.5 text-right font-medium">
                            {row.same_distribution ? (
                              <Badge
                                variant="outline"
                                className="bg-success/15 text-success border-success/30 text-[10px]"
                              >
                                Same Dist (p &gt; α)
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className="bg-amber-500/15 text-amber-500 border-amber-500/30 text-[10px]"
                              >
                                Reject (p &lt; α)
                              </Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Decode-only benchmark note */}
                {data.timing.decode_only_us && (
                  <div className="p-2.5 rounded-lg bg-bg-elevated/70 border border-border text-xs text-text-secondary space-y-1">
                    <div className="flex items-center gap-1.5 font-semibold text-text-primary">
                      <Sparkles size={13} className="text-accent" />
                      <span>Entry DTE Decode-Only ({data.timing.decode_only_us.rounds.toLocaleString()} rounds, no KDF):</span>
                    </div>
                    <p className="leading-relaxed">
                      Real seeds decode in <strong className="text-text-primary font-mono">{data.timing.decode_only_us.real_seeds.p50.toFixed(1)} µs</strong> p50 ({data.timing.decode_only_us.real_seeds.p95.toFixed(1)} µs p95) vs random seeds in <strong className="text-text-primary font-mono">{data.timing.decode_only_us.random_seeds.p50.toFixed(1)} µs</strong> p50 ({data.timing.decode_only_us.random_seeds.p95.toFixed(1)} µs p95) (KS p &lt; 10⁻³⁰⁰). Decode never exits early; ~42 µs divergence reflects value-dependent template complexity of unusual strings, not a key verification oracle (§4.5).
                    </p>
                  </div>
                )}
              </div>
            )}

            {data.timing && (
              <div className="mt-3 p-2.5 rounded-lg bg-bg-elevated/60 border border-border/60 text-xs text-text-secondary flex items-start gap-2">
                <span className="text-info font-bold shrink-0">Timing Invariant:</span>
                <span>
                  Two-sample Kolmogorov-Smirnov test (n={data.timing.n_per_class} per class, interleaved) shows no detectable timing difference between right and wrong master passwords for vault unlock at default (p = {formatPValue(data.timing.profiles.default?.ks_p_value)}) and server_lite (p = {formatPValue(data.timing.profiles.server_lite?.ks_p_value)}). See{' '}
                  <a
                    href="https://github.com/rohansd05/CNS---Honey-Encryption-Vault/blob/dev/docs/eval-report.md#45-timing-no-difference-at-default-a-small-value-dependent-decode-cost"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent underline font-semibold inline-flex items-center gap-1 hover:text-accent-hover"
                  >
                    <span>docs/eval-report.md §4.5</span>
                    <ExternalLink size={11} />
                  </a>
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
