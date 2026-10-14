// owner: Chetan (T3) — eval mock handlers (feat/t3-eval-v3-ui)
import { http, HttpResponse } from 'msw';
import type { EvalSummaryResponse } from '@/api/types';

// Exact copy of backend/eval/results/latest.json
export const MOCK_EVAL_SUMMARY: EvalSummaryResponse = {
  "timestamp": "2026-10-14T16:11:22Z",
  "version": "1.0.0",
  "dataset": {
    "corpus": "SecLists RockYou, Zipf-ranked weights; usernames: SecLists xato-net, Zipf-ranked",
    "training_samples": null,
    "test_samples": 50000,
    "heldout_passwords_file": "data/processed/heldout_passwords.tsv",
    "heldout_usernames_file": "data/processed/heldout_usernames.tsv",
    "models": {
      "password_model": "pcfg-password-v1",
      "username_model": "pcfg-username-v1",
      "entry_seed_len": 532
    }
  },
  "round_trip": {
    "trials": 25000,
    "exact_match_count": 25000,
    "success_rate": 1.0,
    "decode_totality": {
      "random_seed_trials": 60000,
      "failed_decodes": 0,
      "totality_rate": 1.0,
      "per_dte": {
        "password": {
          "random_seed_trials": 20000,
          "failed_decodes": 0,
          "totality_rate": 1.0
        },
        "username": {
          "random_seed_trials": 20000,
          "failed_decodes": 0,
          "totality_rate": 1.0
        },
        "entry": {
          "random_seed_trials": 20000,
          "failed_decodes": 0,
          "totality_rate": 1.0
        }
      }
    },
    "passwords": {
      "trials": 10000,
      "exact_match_count": 10000,
      "success_rate": 1.0,
      "wrong_seed_length": 0,
      "errors": {},
      "source": "heldout"
    },
    "usernames": {
      "trials": 10000,
      "exact_match_count": 10000,
      "success_rate": 1.0,
      "wrong_seed_length": 0,
      "errors": {},
      "source": "heldout"
    },
    "entries": {
      "trials": 5000,
      "exact_match_count": 5000,
      "success_rate": 1.0,
      "wrong_seed_length": 0,
      "errors": {},
      "source": "(username, password) pairs from the two sets above; heldout"
    },
    "heldout_passwords_available": 50000
  },
  "chi_squared": {
    "n": 20000,
    "seed": 7,
    "alpha": 0.05,
    "interpretation": "p > 0.05: no evidence of deviation (uniform seeds / decoys follow the model)",
    "password": {
      "model": "pcfg-password-v1",
      "seed_byte_uniformity": {
        "test": "seed_byte_uniformity",
        "n": 20000,
        "chi2": 434.4442181818182,
        "dof": 255,
        "p_value": 1.683666192325883e-11
      },
      "seed_int_uniformity": {
        "test": "seed_int_uniformity",
        "n": 20000,
        "chi2": 417.67069446178175,
        "dof": 15,
        "p_value": 1.3311233754473868e-79
      },
      "seed_int_uniformity_control": {
        "test": "seed_int_uniformity_control",
        "n": 20000,
        "chi2": 16.117458581993226,
        "dof": 15,
        "p_value": 0.37428853188827826
      },
      "template_goodness_of_fit": {
        "test": "template_goodness_of_fit",
        "n": 20000,
        "chi2": 36.40386773653889,
        "dof": 50,
        "p_value": 0.924881426235355
      }
    },
    "username": {
      "model": "pcfg-username-v1",
      "seed_byte_uniformity": {
        "test": "seed_byte_uniformity",
        "n": 20000,
        "chi2": 920.4524895522388,
        "dof": 255,
        "p_value": 5.065617465619962e-76
      },
      "seed_int_uniformity": {
        "test": "seed_int_uniformity",
        "n": 20000,
        "chi2": 1364.8609026170423,
        "dof": 15,
        "p_value": 5.9926334056259406e-282
      },
      "seed_int_uniformity_control": {
        "test": "seed_int_uniformity_control",
        "n": 20000,
        "chi2": 21.20187025131502,
        "dof": 15,
        "p_value": 0.13050254820828155
      },
      "template_goodness_of_fit": {
        "test": "template_goodness_of_fit",
        "n": 20000,
        "chi2": 54.534398953305455,
        "dof": 50,
        "p_value": 0.3061978786400413
      }
    },
    "seed_uniformity": {
      "statistic": 434.4442181818182,
      "degrees_of_freedom": 255,
      "p_value": 1.683666192325883e-11,
      "null_hypothesis_accepted": false,
      "note": "Password model: bytes of seeds from encoding held-out passwords vs uniform (256 bins)",
      "n": 20000
    },
    "template_goodness_of_fit": {
      "statistic": 36.40386773653889,
      "degrees_of_freedom": 50,
      "p_value": 0.924881426235355,
      "null_hypothesis_accepted": true,
      "note": "Password model: templates of decoded random seeds vs model probabilities",
      "n": 20000
    }
  },
  "classifier": {
    "password": {
      "n": 10000,
      "logreg": {
        "accuracy_mean": 0.5173,
        "accuracy_std": 0.010240117186829465,
        "roc_auc_mean": 0.527569475
      },
      "random_forest": {
        "accuracy_mean": 0.7401500000000001,
        "accuracy_std": 0.005129814811472232,
        "roc_auc_mean": 0.8052428749999999
      },
      "interpretation": "≈0.5 = indistinguishable",
      "grouped": {
        "n": 10000,
        "distinct_strings": 11455,
        "logreg": {
          "accuracy_mean": 0.4619,
          "accuracy_std": 0.061808292323926886,
          "roc_auc_mean": 0.45409637499999994
        },
        "random_forest": {
          "accuracy_mean": 0.5167499999999999,
          "accuracy_std": 0.04468333022504028,
          "roc_auc_mean": 0.5091537999999999
        }
      },
      "distinct": {
        "n": 5687,
        "distinct_real": 6007,
        "distinct_decoy": 5687,
        "logreg": {
          "accuracy_mean": 0.5437839697681385,
          "accuracy_std": 0.0031756813160750343,
          "roc_auc_mean": 0.5671294494047308
        },
        "random_forest": {
          "accuracy_mean": 0.5072088685281297,
          "accuracy_std": 0.008716550394147574,
          "roc_auc_mean": 0.5187300687784979
        }
      }
    },
    "username": {
      "n": 10000,
      "logreg": {
        "accuracy_mean": 0.7337499999999999,
        "accuracy_std": 0.0038470768123342967,
        "roc_auc_mean": 0.7933458250000001
      },
      "random_forest": {
        "accuracy_mean": 0.827,
        "accuracy_std": 0.005424481542046212,
        "roc_auc_mean": 0.9147115250000001
      },
      "interpretation": "≈0.5 = indistinguishable",
      "grouped": {
        "n": 10000,
        "distinct_strings": 11998,
        "logreg": {
          "accuracy_mean": 0.72805,
          "accuracy_std": 0.010856334556377696,
          "roc_auc_mean": 0.7819294750000001
        },
        "random_forest": {
          "accuracy_mean": 0.5630499999999999,
          "accuracy_std": 0.08797576370796673,
          "roc_auc_mean": 0.7133034500000001
        }
      },
      "distinct": {
        "n": 4378,
        "distinct_real": 4378,
        "distinct_decoy": 7681,
        "logreg": {
          "accuracy_mean": 0.7592501610299659,
          "accuracy_std": 0.007141104400344822,
          "roc_auc_mean": 0.7840525525203512
        },
        "random_forest": {
          "accuracy_mean": 0.6772497255319204,
          "accuracy_std": 0.005947675527020168,
          "roc_auc_mean": 0.7627338641217418
        }
      },
      "without_domain": {
        "n": 10000,
        "logreg": {
          "accuracy_mean": 0.57145,
          "accuracy_std": 0.003909603560464944,
          "roc_auc_mean": 0.6237055
        },
        "random_forest": {
          "accuracy_mean": 0.78265,
          "accuracy_std": 0.00390704491911723,
          "roc_auc_mean": 0.8626568499999999
        },
        "interpretation": "≈0.5 = indistinguishable",
        "transformed": {
          "real": 0,
          "decoy": 4554
        },
        "grouped": {
          "n": 10000,
          "distinct_strings": 10430,
          "logreg": {
            "accuracy_mean": 0.5533834341929114,
            "accuracy_std": 0.05863205751438029,
            "roc_auc_mean": 0.5749826455226292
          },
          "random_forest": {
            "accuracy_mean": 0.5459230610785871,
            "accuracy_std": 0.09180538148790511,
            "roc_auc_mean": 0.5618266066725874
          }
        },
        "distinct": {
          "n": 4378,
          "distinct_real": 4378,
          "distinct_decoy": 6153,
          "logreg": {
            "accuracy_mean": 0.5574468209946566,
            "accuracy_std": 0.010946732510834847,
            "roc_auc_mean": 0.5796859804245711
          },
          "random_forest": {
            "accuracy_mean": 0.5277517217819432,
            "accuracy_std": 0.011060822886659093,
            "roc_auc_mean": 0.5383541959687485
          }
        },
        "note": "known email domains (the username model's table) stripped from real and decoy values before features; same real sample, fresh decoys"
      }
    }
  },
  "distinguisher": {
    "classifier": "Logistic Regression + Random Forest (5-fold stratified CV)",
    "features": [
      "length",
      "n_lower",
      "n_upper",
      "n_digit",
      "n_symbol",
      "n_segments",
      "template_logprob",
      "mean_char_unigram_logprob",
      "longest_digit_run",
      "starts_with_capital",
      "ends_with_digit",
      "shannon_entropy"
    ],
    "metrics": {
      "accuracy": 0.7401500000000001,
      "roc_auc": 0.8052428749999999,
      "precision": 0.7297618237894935,
      "recall": 0.7617999999999999,
      "baseline_chance": 0.5
    },
    "metrics_classifier": "random_forest",
    "per_classifier": {
      "logreg": {
        "accuracy_mean": 0.5173,
        "accuracy_std": 0.010240117186829465,
        "roc_auc_mean": 0.527569475
      },
      "random_forest": {
        "accuracy_mean": 0.7401500000000001,
        "accuracy_std": 0.005129814811472232,
        "roc_auc_mean": 0.8052428749999999
      }
    },
    "grouped_results": {
      "logreg": {
        "accuracy_mean": 0.4619,
        "accuracy_std": 0.061808292323926886,
        "roc_auc_mean": 0.45409637499999994
      },
      "random_forest": {
        "accuracy_mean": 0.5167499999999999,
        "accuracy_std": 0.04468333022504028,
        "roc_auc_mean": 0.5091537999999999
      }
    },
    "distinct_results": {
      "logreg": {
        "accuracy_mean": 0.5437839697681385,
        "accuracy_std": 0.0031756813160750343,
        "roc_auc_mean": 0.5671294494047308
      },
      "random_forest": {
        "accuracy_mean": 0.5072088685281297,
        "accuracy_std": 0.008716550394147574,
        "roc_auc_mean": 0.5187300687784979
      }
    },
    "n_per_class": 10000,
    "target_accuracy": 0.6,
    "ideal_accuracy": 0.5,
    "conclusion": "Password distinguisher (random_forest) accuracy 0.740 vs ideal 0.5: misses the <= 0.60 target: the classifier separates real passwords from decoys. Best accuracy with grouped CV (no string in both train and test) 0.517; on distinct strings only 0.544."
  },
  "template_frequencies": [
    {
      "template": "L6",
      "model_frequency": 0.21192,
      "decoded_frequency": 0.21015,
      "heldout_frequency": 0.21335,
      "description": "6 letters"
    },
    {
      "template": "L7",
      "model_frequency": 0.1262,
      "decoded_frequency": 0.12665,
      "heldout_frequency": 0.15065,
      "description": "7 letters"
    },
    {
      "template": "D6",
      "model_frequency": 0.12018,
      "decoded_frequency": 0.1212,
      "heldout_frequency": 0.0905,
      "description": "6 digits"
    },
    {
      "template": "L8",
      "model_frequency": 0.11334,
      "decoded_frequency": 0.11095,
      "heldout_frequency": 0.1133,
      "description": "8 letters"
    },
    {
      "template": "L9",
      "model_frequency": 0.04878,
      "decoded_frequency": 0.04835,
      "heldout_frequency": 0.0421,
      "description": "9 letters"
    },
    {
      "template": "L5",
      "model_frequency": 0.04296,
      "decoded_frequency": 0.0438,
      "heldout_frequency": 0.05835,
      "description": "5 letters"
    },
    {
      "template": "L6D1",
      "model_frequency": 0.02644,
      "decoded_frequency": 0.02625,
      "heldout_frequency": 0.03155,
      "description": "6 letters + 1 digit"
    },
    {
      "template": "D5",
      "model_frequency": 0.02587,
      "decoded_frequency": 0.0261,
      "heldout_frequency": 0.0033,
      "description": "5 digits"
    },
    {
      "template": "L6D2",
      "model_frequency": 0.02369,
      "decoded_frequency": 0.02505,
      "heldout_frequency": 0.02725,
      "description": "6 letters + 2 digits"
    },
    {
      "template": "L10",
      "model_frequency": 0.02322,
      "decoded_frequency": 0.02315,
      "heldout_frequency": 0.02135,
      "description": "10 letters"
    },
    {
      "template": "L5D2",
      "model_frequency": 0.02201,
      "decoded_frequency": 0.0244,
      "heldout_frequency": 0.01985,
      "description": "5 letters + 2 digits"
    },
    {
      "template": "L5D1",
      "model_frequency": 0.02112,
      "decoded_frequency": 0.0221,
      "heldout_frequency": 0.0272,
      "description": "5 letters + 1 digit"
    },
    {
      "template": "D8",
      "model_frequency": 0.02065,
      "decoded_frequency": 0.0207,
      "heldout_frequency": 0.01695,
      "description": "8 digits"
    },
    {
      "template": "L4D2",
      "model_frequency": 0.01949,
      "decoded_frequency": 0.0196,
      "heldout_frequency": 0.0187,
      "description": "4 letters + 2 digits"
    },
    {
      "template": "L7D1",
      "model_frequency": 0.01863,
      "decoded_frequency": 0.01885,
      "heldout_frequency": 0.01955,
      "description": "7 letters + 1 digit"
    }
  ],
  "attack": {
    "kdf_profile": "demo",
    "entries_per_vault": 8,
    "wordlist": "attack/wordlists/demo_wordlist.txt",
    "wordlist_size": 629,
    "guesses": 500,
    "real_guess_index": 193,
    "conventional": {
      "cracked": true,
      "guess_index": 193,
      "elapsed_ms": 1413,
      "recovered_entries": 8,
      "recovered_entries_are_real": true
    },
    "honey": {
      "guesses_tried": 500,
      "elapsed_ms": 3580,
      "ms_per_guess": 7.16,
      "distinct_vaults": 500,
      "distinct_vault_rate": 1.0,
      "samples_returned": 25,
      "sample_fields_well_formed": true,
      "correct_password_recovers_real_entries": true
    }
  },
  "kdf": {
    "default": {
      "params": {
        "time_cost": 3,
        "memory_cost_kib": 65536,
        "parallelism": 4,
        "hash_len": 32
      },
      "reps": 15,
      "derive_ms": {
        "p50": 85.1,
        "p95": 202.02,
        "mean": 98.74,
        "min": 50.74,
        "max": 231.59
      },
      "unlock_ms": {
        "p50": 54.48,
        "p95": 151.5,
        "mean": 70.05,
        "min": 51.71,
        "max": 167.09
      }
    },
    "server_lite": {
      "params": {
        "time_cost": 2,
        "memory_cost_kib": 19456,
        "parallelism": 1,
        "hash_len": 32
      },
      "reps": 15,
      "derive_ms": {
        "p50": 25.98,
        "p95": 30.48,
        "mean": 26.52,
        "min": 25.33,
        "max": 30.78
      },
      "unlock_ms": {
        "p50": 26.67,
        "p95": 30.12,
        "mean": 27.2,
        "min": 25.47,
        "max": 30.54
      }
    },
    "demo": {
      "params": {
        "time_cost": 1,
        "memory_cost_kib": 8192,
        "parallelism": 1,
        "hash_len": 32
      },
      "reps": 15,
      "derive_ms": {
        "p50": 7.5,
        "p95": 12.68,
        "mean": 8.5,
        "min": 6.76,
        "max": 23.22
      },
      "unlock_ms": {
        "p50": 7.47,
        "p95": 8.23,
        "mean": 7.47,
        "min": 6.79,
        "max": 8.25
      }
    }
  },
  "timing": {
    "n_per_class": 200,
    "entries": 8,
    "alpha": 0.05,
    "method": "in-process HoneyVault.unlock, right vs fresh wrong master password (plus a second right sample as A/A control), interleaved; two-sample Kolmogorov-Smirnov test",
    "profiles": {
      "default": {
        "right_ms": {
          "p50": 53.18,
          "p95": 195.78,
          "mean": 77.9,
          "min": 41.09,
          "max": 478.0
        },
        "wrong_ms": {
          "p50": 53.67,
          "p95": 199.73,
          "mean": 80.69,
          "min": 40.84,
          "max": 653.2
        },
        "ks_statistic": 0.06000000000000005,
        "ks_p_value": 0.8655265369450457,
        "same_distribution": true,
        "control_ks_p_value": 0.46628639073563594
      },
      "server_lite": {
        "right_ms": {
          "p50": 27.3,
          "p95": 54.6,
          "mean": 32.68,
          "min": 21.05,
          "max": 150.26
        },
        "wrong_ms": {
          "p50": 27.17,
          "p95": 52.69,
          "mean": 32.45,
          "min": 20.89,
          "max": 150.51
        },
        "ks_statistic": 0.09000000000000002,
        "ks_p_value": 0.39352743357720954,
        "same_distribution": true,
        "control_ks_p_value": 0.9646522162314058
      },
      "demo": {
        "right_ms": {
          "p50": 5.98,
          "p95": 8.34,
          "mean": 6.63,
          "min": 5.28,
          "max": 37.86
        },
        "wrong_ms": {
          "p50": 5.93,
          "p95": 7.78,
          "mean": 6.23,
          "min": 5.18,
          "max": 10.14
        },
        "ks_statistic": 0.125,
        "ks_p_value": 0.0878382826713132,
        "same_distribution": true,
        "control_ks_p_value": 0.1420746514551761
      }
    },
    "decode_only_us": {
      "rounds": 2000,
      "real_seeds": {
        "p50": 86.5,
        "p95": 109.22,
        "mean": 89.99,
        "min": 82.8,
        "max": 204.3
      },
      "random_seeds": {
        "p50": 44.9,
        "p95": 54.41,
        "mean": 46.44,
        "min": 37.6,
        "max": 117.2
      },
      "ks_p_value": 0.0
    }
  },
  "performance": {
    "unlock_p50_ms": 54.48,
    "unlock_p95_ms": 151.5,
    "target_p95_ms": 1500,
    "argon2_kdf_profile": "default (t=3, m=64 MiB, p=4)",
    "entries": 8,
    "measured": "in-process HoneyVault.unlock (no HTTP); see kdf for every profile"
  },
  "meta": {
    "git_commit": "91e3171",
    "timestamp": "2026-10-14T16:11:22Z",
    "mode": "full",
    "seed": 7,
    "config": {
      "round_trip_passwords": 10000,
      "round_trip_usernames": 10000,
      "round_trip_entries": 5000,
      "totality_seeds": 20000,
      "chi_n": 20000,
      "classifier_n": 10000,
      "template_n": 20000,
      "attack_guesses": 500,
      "kdf_reps": 15,
      "timing_n": 200
    },
    "models": {
      "password_model": "pcfg-password-v1",
      "username_model": "pcfg-username-v1",
      "entry_seed_len": 532
    },
    "entry_dte_impl": "honeycore.dte.entry_dte.PCFGEntryDTE",
    "honeycore_impl": "real",
    "dataset_note": "SecLists RockYou, Zipf-ranked weights; usernames: SecLists xato-net, Zipf-ranked",
    "python": "3.12.10",
    "platform": "Windows-11",
    "step_seconds": {
      "round_trip": 3.03,
      "chi_squared": 7.51,
      "template_frequencies": 0.39,
      "classifier": 112.85,
      "attack": 5.33,
      "kdf": 4.96,
      "timing": 73.65
    },
    "duration_s": 208.47,
    "reproducibility": "held-out sampling, random seeds and CV folds use NumPy RNG(seed); decoys (model.sample), vault salts/nonces and the attack password use `secrets`, so classifier/attack numbers vary slightly between runs"
  }
};

export const evalHandlers = [
  // GET /api/eval/summary
  http.get('/api/eval/summary', () => {
    return HttpResponse.json<EvalSummaryResponse>(MOCK_EVAL_SUMMARY);
  }),
];
