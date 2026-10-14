// owner: Chetan (T3) — evaluation types & schema (feat/t3-eval-real-data)

export interface EvalDatasetModels {
  password_model?: string;
  username_model?: string;
  entry_seed_len?: number;
}

export interface EvalDataset {
  corpus?: string;
  training_samples?: number | null;
  test_samples?: number | null;
  heldout_passwords_file?: string | null;
  heldout_usernames_file?: string | null;
  models?: EvalDatasetModels;
}

export interface DecodeTotalityPerDte {
  random_seed_trials?: number;
  failed_decodes?: number;
  totality_rate?: number;
}

export interface DecodeTotality {
  random_seed_trials: number;
  failed_decodes: number;
  totality_rate: number;
  per_dte?: Record<string, DecodeTotalityPerDte>;
}

export interface EvalRoundTripDetail {
  trials?: number;
  exact_match_count?: number;
  success_rate?: number;
  wrong_seed_length?: number;
  errors?: Record<string, unknown>;
  source?: string;
}

export interface EvalRoundTrip {
  trials: number;
  exact_match_count: number;
  success_rate: number;
  decode_totality: DecodeTotality;
  passwords?: EvalRoundTripDetail;
  usernames?: EvalRoundTripDetail;
  entries?: EvalRoundTripDetail;
  heldout_passwords_available?: number;
}

export interface ChiSquaredTestResult {
  statistic?: number;
  degrees_of_freedom?: number;
  p_value: number;
  null_hypothesis_accepted?: boolean;
  note?: string;
  n?: number;
  test?: string;
  chi2?: number;
  dof?: number;
}

export interface ChiSquaredModelTests {
  model?: string;
  skipped?: string;
  seed_byte_uniformity?: ChiSquaredTestResult;
  seed_int_uniformity?: ChiSquaredTestResult;
  seed_int_uniformity_control?: ChiSquaredTestResult;
  template_goodness_of_fit?: ChiSquaredTestResult;
}

export interface EvalChiSquared {
  n?: number;
  seed?: number;
  alpha?: number;
  interpretation?: string;
  password?: ChiSquaredModelTests;
  username?: ChiSquaredModelTests;
  seed_uniformity?: ChiSquaredTestResult;
  template_goodness_of_fit?: ChiSquaredTestResult;
}

export interface ClassifierScore {
  accuracy_mean: number;
  accuracy_std: number;
  roc_auc_mean: number;
}

export interface ClassifierGroupedScore {
  n?: number;
  distinct_strings?: number;
  logreg: ClassifierScore;
  random_forest: ClassifierScore;
}

export interface ClassifierDistinctScore {
  n?: number;
  distinct_real?: number;
  distinct_decoy?: number;
  logreg: ClassifierScore;
  random_forest: ClassifierScore;
}

export interface ClassifierWithoutDomain {
  n: number;
  logreg: ClassifierScore;
  random_forest: ClassifierScore;
  interpretation?: string;
  transformed?: {
    real: number;
    decoy: number;
  };
  grouped?: ClassifierGroupedScore;
  distinct?: ClassifierDistinctScore;
  note?: string;
}

export interface FieldClassifierResult {
  n: number;
  logreg: ClassifierScore;
  random_forest: ClassifierScore;
  interpretation?: string;
  grouped?: ClassifierGroupedScore;
  distinct?: ClassifierDistinctScore;
  without_domain?: ClassifierWithoutDomain;
}

export interface EvalClassifier {
  password?: FieldClassifierResult;
  username?: FieldClassifierResult;
}

export interface DistinguisherMetrics {
  accuracy: number;
  roc_auc: number;
  precision?: number;
  recall?: number;
  baseline_chance: number;
}

export interface ClassifierPair {
  logreg?: ClassifierScore;
  random_forest?: ClassifierScore;
  [key: string]: ClassifierScore | undefined;
}

export interface EvalDistinguisher {
  classifier: string;
  features: string[];
  metrics: DistinguisherMetrics;
  metrics_classifier?: string;
  per_classifier?: ClassifierPair;
  grouped_results?: ClassifierPair;
  distinct_results?: ClassifierPair;
  target_accuracy: number;
  ideal_accuracy: number;
  conclusion?: string;
  n_per_class?: number;
}

export interface TemplateFrequencyItem {
  template: string;
  model_frequency: number;
  decoded_frequency: number;
  heldout_frequency?: number;
  description?: string;
}

export interface AttackConventional {
  cracked: boolean;
  guess_index: number | null;
  elapsed_ms: number;
  recovered_entries: number;
  recovered_entries_are_real?: boolean;
}

export interface AttackHoney {
  guesses_tried: number;
  elapsed_ms: number;
  ms_per_guess?: number;
  distinct_vaults: number;
  distinct_vault_rate?: number;
  samples_returned?: number;
  sample_fields_well_formed?: boolean;
  correct_password_recovers_real_entries?: boolean;
}

export interface EvalAttack {
  kdf_profile?: string;
  entries_per_vault?: number;
  wordlist?: string;
  wordlist_size?: number;
  guesses: number;
  real_guess_index?: number;
  conventional: AttackConventional;
  honey: AttackHoney;
}

export interface KdfProfileParams {
  time_cost: number;
  memory_cost_kib: number;
  parallelism: number;
  hash_len: number;
}

export interface KdfLatencyStats {
  p50: number;
  p95: number;
  mean?: number;
  min?: number;
  max?: number;
}

export interface KdfProfile {
  params: KdfProfileParams;
  reps?: number;
  derive_ms?: KdfLatencyStats;
  unlock_ms: KdfLatencyStats;
}

export interface EvalPerformance {
  unlock_p50_ms: number;
  unlock_p95_ms: number;
  target_p95_ms: number;
  argon2_kdf_profile?: string;
  entries?: number;
  measured?: string;
}

export interface EvalMeta {
  git_commit?: string;
  timestamp?: string;
  mode?: string;
  seed?: number;
  config?: Record<string, unknown>;
  models?: Record<string, unknown>;
  entry_dte_impl?: string;
  honeycore_impl?: string;
  dataset_note?: string;
  python?: string;
  platform?: string;
  step_seconds?: Record<string, number>;
  duration_s?: number;
  reproducibility?: string;
}

export interface TimingLatencyStats {
  p50: number;
  p95: number;
  mean?: number;
  min?: number;
  max?: number;
}

export interface TimingProfileResult {
  right_ms: TimingLatencyStats;
  wrong_ms: TimingLatencyStats;
  ks_statistic: number;
  ks_p_value: number;
  same_distribution: boolean;
  control_ks_p_value?: number;
}

export interface TimingDecodeOnlyStats {
  rounds: number;
  real_seeds: TimingLatencyStats;
  random_seeds: TimingLatencyStats;
  ks_p_value: number;
}

export interface TimingProfilesMap {
  default?: TimingProfileResult;
  server_lite?: TimingProfileResult;
  demo?: TimingProfileResult;
  [key: string]: TimingProfileResult | undefined;
}

export interface EvalTiming {
  n_per_class: number;
  entries: number;
  alpha?: number;
  method?: string;
  profiles: TimingProfilesMap;
  decode_only_us?: TimingDecodeOnlyStats;
}

export interface EvalSummaryData {
  timestamp: string;
  version: string;
  dataset?: EvalDataset;
  round_trip: EvalRoundTrip;
  chi_squared: EvalChiSquared;
  classifier?: EvalClassifier;
  distinguisher: EvalDistinguisher;
  template_frequencies?: TemplateFrequencyItem[];
  attack?: EvalAttack;
  kdf?: Record<string, KdfProfile>;
  performance: EvalPerformance;
  timing?: EvalTiming;
  meta?: EvalMeta;
}
