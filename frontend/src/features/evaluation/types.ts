// owner: Chetan (T3) — evaluation types & schema (feat/t3-evaluation-admin)

export interface EvalDatasetModels {
  password_model: string;
  username_model: string;
  entry_seed_len: number;
}

export interface EvalDataset {
  corpus: string;
  training_samples: number;
  test_samples: number;
  models: EvalDatasetModels;
}

export interface DecodeTotality {
  random_seed_trials: number;
  failed_decodes: number;
  totality_rate: number;
}

export interface EvalRoundTrip {
  trials: number;
  exact_match_count: number;
  success_rate: number;
  decode_totality: DecodeTotality;
}

export interface ChiSquaredTestResult {
  statistic: number;
  degrees_of_freedom: number;
  p_value: number;
  null_hypothesis_accepted: boolean;
  note: string;
}

export interface EvalChiSquared {
  seed_uniformity: ChiSquaredTestResult;
  template_goodness_of_fit: ChiSquaredTestResult;
}

export interface DistinguisherMetrics {
  accuracy: number;
  roc_auc: number;
  precision: number;
  recall: number;
  baseline_chance: number;
}

export interface EvalDistinguisher {
  classifier: string;
  features: string[];
  metrics: DistinguisherMetrics;
  target_accuracy: number;
  ideal_accuracy: number;
  conclusion: string;
}

export interface TemplateFrequencyItem {
  template: string;
  model_frequency: number;
  decoded_frequency: number;
  description: string;
}

export interface EvalPerformance {
  unlock_p50_ms: number;
  unlock_p95_ms: number;
  target_p95_ms: number;
  argon2_kdf_profile: string;
}

export interface EvalSummaryData {
  timestamp: string;
  version: string;
  dataset: EvalDataset;
  round_trip: EvalRoundTrip;
  chi_squared: EvalChiSquared;
  distinguisher: EvalDistinguisher;
  template_frequencies: TemplateFrequencyItem[];
  performance: EvalPerformance;
}
