// owner: Chetan (T3) — eval mock handlers (feat/t3-attack-lab)
import { http, HttpResponse } from 'msw';
import type { EvalSummaryResponse } from '@/api/types';

export const MOCK_EVAL_SUMMARY: EvalSummaryResponse = {
  timestamp: '2026-10-05T12:00:00Z',
  version: '1.0.0',
  dataset: {
    corpus: 'RockYou2021 + SecLists xato usernames (80/20 train/test split)',
    training_samples: 800000,
    test_samples: 200000,
    models: {
      password_model: 'pcfg-password-v1',
      username_model: 'pcfg-username-v1',
      entry_seed_len: 532,
    },
  },
  round_trip: {
    trials: 50000,
    exact_match_count: 50000,
    success_rate: 1.0,
    decode_totality: {
      random_seed_trials: 100000,
      failed_decodes: 0,
      totality_rate: 1.0,
    },
  },
  chi_squared: {
    seed_uniformity: {
      statistic: 248.32,
      degrees_of_freedom: 255,
      p_value: 0.612,
      null_hypothesis_accepted: true,
      note: 'Encoding held-out passwords produces byte distributions indistinguishable from uniform noise (p > 0.05)',
    },
    template_goodness_of_fit: {
      statistic: 18.45,
      degrees_of_freedom: 19,
      p_value: 0.492,
      null_hypothesis_accepted: true,
      note: 'Decoded random seeds match target PCFG template distribution (goodness of fit p > 0.05)',
    },
  },
  distinguisher: {
    classifier: 'Logistic Regression + Random Forest (5-fold CV)',
    features: ['password_length', 'char_class_counts', 'template_log_prob', 'shannon_entropy'],
    metrics: {
      accuracy: 0.548,
      roc_auc: 0.552,
      precision: 0.545,
      recall: 0.551,
      baseline_chance: 0.5,
    },
    target_accuracy: 0.6,
    ideal_accuracy: 0.5,
    conclusion: 'Near-ideal confusion; classifier cannot reliably distinguish real decrypted vaults from random decoys (target <= 0.60, actual 0.548)',
  },
  template_frequencies: [
    { template: 'L6D2', model_frequency: 0.285, decoded_frequency: 0.282, description: '6 letters + 2 digits (e.g. dragon88)' },
    { template: 'L8D1', model_frequency: 0.174, decoded_frequency: 0.176, description: '8 letters + 1 digit (e.g. password1)' },
    { template: 'L5D3', model_frequency: 0.142, decoded_frequency: 0.14, description: '5 letters + 3 digits (e.g. monkey123)' },
    { template: 'L6S1D2', model_frequency: 0.118, decoded_frequency: 0.121, description: '6 letters + symbol + 2 digits (e.g. secret!26)' },
    { template: 'L7D2', model_frequency: 0.105, decoded_frequency: 0.103, description: '7 letters + 2 digits (e.g. sunshine99)' },
    { template: 'L8S1', model_frequency: 0.089, decoded_frequency: 0.091, description: '8 letters + 1 symbol (e.g. princess#)' },
    { template: 'OTHER', model_frequency: 0.087, decoded_frequency: 0.087, description: 'Longer/mixed tail distributions' },
  ],
  performance: {
    unlock_p50_ms: 340,
    unlock_p95_ms: 780,
    target_p95_ms: 1500,
    argon2_kdf_profile: 'demo (t=3, m=64MB, p=4)',
  },
};

export const evalHandlers = [
  // GET /api/eval/summary
  http.get('/api/eval/summary', () => {
    return HttpResponse.json<EvalSummaryResponse>(MOCK_EVAL_SUMMARY);
  }),
];
