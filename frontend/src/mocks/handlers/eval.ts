// owner: Chetan (T3) — eval mock handlers (feat/t3-eval-v3-ui)
import { http, HttpResponse } from 'msw';
import type { EvalSummaryResponse } from '@/api/types';

// Exact copy of backend/eval/results/latest.json
export const MOCK_EVAL_SUMMARY: EvalSummaryResponse = {
  "timestamp": "2026-10-17T08:30:07Z",
  "version": "1.0.0",
  "dataset": {
    "corpus": "passwords: RockYou rockyou-withcount, real counts (pcfg-password-v2); usernames: SecLists xato-net, Zipf-ranked (pcfg-username-v1)",
    "training_samples": null,
    "test_samples": 50000,
    "heldout_passwords_file": "data/processed/heldout_passwords.tsv",
    "heldout_usernames_file": "data/processed/heldout_usernames.tsv",
    "models": {
      "password_model": "pcfg-password-v2",
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
      "model": "pcfg-password-v2",
      "seed_byte_uniformity": {
        "test": "seed_byte_uniformity",
        "n": 20000,
        "chi2": 275.13299393939394,
        "dof": 255,
        "p_value": 0.18448540285225165
      },
      "seed_int_uniformity": {
        "test": "seed_int_uniformity",
        "n": 20000,
        "chi2": 9.367393466452452,
        "dof": 15,
        "p_value": 0.8575376835775853
      },
      "seed_int_uniformity_control": {
        "test": "seed_int_uniformity_control",
        "n": 20000,
        "chi2": 7.120768554265357,
        "dof": 15,
        "p_value": 0.9542114010986245
      },
      "seed_pit_uniformity": {
        "test": "seed_pit_uniformity",
        "n": 20000,
        "chi2": 1634.5230510289955,
        "dof": 15,
        "p_value": 0.0,
        "ints": 130710
      },
      "seed_pit_uniformity_control": {
        "test": "seed_pit_uniformity_control",
        "n": 20000,
        "chi2": 12.535152276670855,
        "dof": 15,
        "p_value": 0.6381536536104393,
        "ints": 66852
      },
      "template_goodness_of_fit": {
        "test": "template_goodness_of_fit",
        "n": 20000,
        "chi2": 46.79357959715795,
        "dof": 50,
        "p_value": 0.6028276562360018
      }
    },
    "username": {
      "model": "pcfg-username-v1",
      "seed_byte_uniformity": {
        "test": "seed_byte_uniformity",
        "n": 20000,
        "chi2": 717.5236776119403,
        "dof": 255,
        "p_value": 1.3674333494628661e-45
      },
      "seed_int_uniformity": {
        "test": "seed_int_uniformity",
        "n": 20000,
        "chi2": 810.8409067314798,
        "dof": 15,
        "p_value": 4.115190074027821e-163
      },
      "seed_int_uniformity_control": {
        "test": "seed_int_uniformity_control",
        "n": 20000,
        "chi2": 11.415904358608426,
        "dof": 15,
        "p_value": 0.7225931717401008
      },
      "seed_pit_uniformity": {
        "test": "seed_pit_uniformity",
        "n": 20000,
        "chi2": 3008.926462415956,
        "dof": 15,
        "p_value": 0.0,
        "ints": 163753
      },
      "seed_pit_uniformity_control": {
        "test": "seed_pit_uniformity_control",
        "n": 20000,
        "chi2": 10.53004198977742,
        "dof": 15,
        "p_value": 0.7851422231236809,
        "ints": 85497
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
      "statistic": 275.13299393939394,
      "degrees_of_freedom": 255,
      "p_value": 0.18448540285225165,
      "null_hypothesis_accepted": true,
      "note": "Password model: bytes of seeds from encoding held-out passwords vs uniform (256 bins)",
      "n": 20000
    },
    "template_goodness_of_fit": {
      "statistic": 46.79357959715795,
      "degrees_of_freedom": 50,
      "p_value": 0.6028276562360018,
      "null_hypothesis_accepted": true,
      "note": "Password model: templates of decoded random seeds vs model probabilities",
      "n": 20000
    }
  },
  "classifier": {
    "password": {
      "n": 10000,
      "logreg": {
        "accuracy_mean": 0.50825,
        "accuracy_std": 0.0072594765651525905,
        "roc_auc_mean": 0.5171327499999999
      },
      "random_forest": {
        "accuracy_mean": 0.74075,
        "accuracy_std": 0.006682065548915242,
        "roc_auc_mean": 0.8151057500000001
      },
      "interpretation": "≈0.5 = indistinguishable",
      "grouped": {
        "n": 10000,
        "distinct_strings": 12287,
        "logreg": {
          "accuracy_mean": 0.4720514736282171,
          "accuracy_std": 0.023916262318084327,
          "roc_auc_mean": 0.4739740542624885
        },
        "random_forest": {
          "accuracy_mean": 0.5192507631937977,
          "accuracy_std": 0.011235504709720194,
          "roc_auc_mean": 0.5322153610152215
        }
      },
      "distinct": {
        "n": 5632,
        "distinct_real": 5632,
        "distinct_decoy": 6721,
        "logreg": {
          "accuracy_mean": 0.5458091007923913,
          "accuracy_std": 0.011256157001513969,
          "roc_auc_mean": 0.5563444098109371
        },
        "random_forest": {
          "accuracy_mean": 0.5190872797194032,
          "accuracy_std": 0.004759488973529036,
          "roc_auc_mean": 0.527602741168083
        }
      }
    },
    "username": {
      "n": 10000,
      "logreg": {
        "accuracy_mean": 0.7134499999999999,
        "accuracy_std": 0.007032780389006901,
        "roc_auc_mean": 0.7430465250000001
      },
      "random_forest": {
        "accuracy_mean": 0.82725,
        "accuracy_std": 0.006659579566308986,
        "roc_auc_mean": 0.9093595750000001
      },
      "interpretation": "≈0.5 = indistinguishable",
      "grouped": {
        "n": 10000,
        "distinct_strings": 12526,
        "logreg": {
          "accuracy_mean": 0.7127993427499589,
          "accuracy_std": 0.00881860453292269,
          "roc_auc_mean": 0.7158202597651587
        },
        "random_forest": {
          "accuracy_mean": 0.6297963773153986,
          "accuracy_std": 0.05600515034476615,
          "roc_auc_mean": 0.7222206112303967
        }
      },
      "distinct": {
        "n": 4908,
        "distinct_real": 4908,
        "distinct_decoy": 7639,
        "logreg": {
          "accuracy_mean": 0.7333939593269788,
          "accuracy_std": 0.005755255083362081,
          "roc_auc_mean": 0.7768520432186388
        },
        "random_forest": {
          "accuracy_mean": 0.6968205591632576,
          "accuracy_std": 0.011399189022139688,
          "roc_auc_mean": 0.7689565882072424
        }
      },
      "without_domain": {
        "n": 10000,
        "logreg": {
          "accuracy_mean": 0.5452,
          "accuracy_std": 0.004817675788178367,
          "roc_auc_mean": 0.5610938750000001
        },
        "random_forest": {
          "accuracy_mean": 0.7673500000000001,
          "accuracy_std": 0.0065069193939989774,
          "roc_auc_mean": 0.85406475
        },
        "interpretation": "≈0.5 = indistinguishable",
        "transformed": {
          "real": 0,
          "decoy": 4515
        },
        "grouped": {
          "n": 10000,
          "distinct_strings": 11101,
          "logreg": {
            "accuracy_mean": 0.5126526248157891,
            "accuracy_std": 0.03936165587878883,
            "roc_auc_mean": 0.5176013442553111
          },
          "random_forest": {
            "accuracy_mean": 0.5324942762902672,
            "accuracy_std": 0.04511910893874989,
            "roc_auc_mean": 0.5298718869381343
          }
        },
        "distinct": {
          "n": 4908,
          "distinct_real": 4908,
          "distinct_decoy": 6219,
          "logreg": {
            "accuracy_mean": 0.5534821385032469,
            "accuracy_std": 0.011339631877422771,
            "roc_auc_mean": 0.5746655240135029
          },
          "random_forest": {
            "accuracy_mean": 0.5226165736180437,
            "accuracy_std": 0.005554866514173579,
            "roc_auc_mean": 0.5371162196170097
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
      "accuracy": 0.74075,
      "roc_auc": 0.8151057500000001,
      "precision": 0.7279208145142988,
      "recall": 0.7537,
      "baseline_chance": 0.5
    },
    "metrics_classifier": "random_forest",
    "per_classifier": {
      "logreg": {
        "accuracy_mean": 0.50825,
        "accuracy_std": 0.0072594765651525905,
        "roc_auc_mean": 0.5171327499999999
      },
      "random_forest": {
        "accuracy_mean": 0.74075,
        "accuracy_std": 0.006682065548915242,
        "roc_auc_mean": 0.8151057500000001
      }
    },
    "grouped_results": {
      "logreg": {
        "accuracy_mean": 0.4720514736282171,
        "accuracy_std": 0.023916262318084327,
        "roc_auc_mean": 0.4739740542624885
      },
      "random_forest": {
        "accuracy_mean": 0.5192507631937977,
        "accuracy_std": 0.011235504709720194,
        "roc_auc_mean": 0.5322153610152215
      }
    },
    "distinct_results": {
      "logreg": {
        "accuracy_mean": 0.5458091007923913,
        "accuracy_std": 0.011256157001513969,
        "roc_auc_mean": 0.5563444098109371
      },
      "random_forest": {
        "accuracy_mean": 0.5190872797194032,
        "accuracy_std": 0.004759488973529036,
        "roc_auc_mean": 0.527602741168083
      }
    },
    "n_per_class": 10000,
    "target_accuracy": 0.6,
    "ideal_accuracy": 0.5,
    "conclusion": "Password distinguisher (random_forest) accuracy 0.741 vs ideal 0.5: misses the <= 0.60 target: the classifier separates real passwords from decoys. Best accuracy with grouped CV (no string in both train and test) 0.519; on distinct strings only 0.546."
  },
  "template_frequencies": [
    {
      "template": "L6",
      "model_frequency": 0.20184,
      "decoded_frequency": 0.20135,
      "heldout_frequency": 0.2214,
      "description": "6 letters"
    },
    {
      "template": "L7",
      "model_frequency": 0.12474,
      "decoded_frequency": 0.12365,
      "heldout_frequency": 0.1107,
      "description": "7 letters"
    },
    {
      "template": "D6",
      "model_frequency": 0.10843,
      "decoded_frequency": 0.10825,
      "heldout_frequency": 0.0911,
      "description": "6 digits"
    },
    {
      "template": "L8",
      "model_frequency": 0.10273,
      "decoded_frequency": 0.10595,
      "heldout_frequency": 0.1173,
      "description": "8 letters"
    },
    {
      "template": "L9",
      "model_frequency": 0.05083,
      "decoded_frequency": 0.04945,
      "heldout_frequency": 0.04825,
      "description": "9 letters"
    },
    {
      "template": "L5",
      "model_frequency": 0.04807,
      "decoded_frequency": 0.0504,
      "heldout_frequency": 0.04585,
      "description": "5 letters"
    },
    {
      "template": "L6D1",
      "model_frequency": 0.03174,
      "decoded_frequency": 0.03255,
      "heldout_frequency": 0.03055,
      "description": "6 letters + 1 digit"
    },
    {
      "template": "L6D2",
      "model_frequency": 0.02864,
      "decoded_frequency": 0.0286,
      "heldout_frequency": 0.0303,
      "description": "6 letters + 2 digits"
    },
    {
      "template": "L5D2",
      "model_frequency": 0.0267,
      "decoded_frequency": 0.0236,
      "heldout_frequency": 0.02885,
      "description": "5 letters + 2 digits"
    },
    {
      "template": "L10",
      "model_frequency": 0.02605,
      "decoded_frequency": 0.02535,
      "heldout_frequency": 0.02495,
      "description": "10 letters"
    },
    {
      "template": "L5D1",
      "model_frequency": 0.02518,
      "decoded_frequency": 0.02525,
      "heldout_frequency": 0.02355,
      "description": "5 letters + 1 digit"
    },
    {
      "template": "L4D2",
      "model_frequency": 0.02357,
      "decoded_frequency": 0.02465,
      "heldout_frequency": 0.02375,
      "description": "4 letters + 2 digits"
    },
    {
      "template": "L7D1",
      "model_frequency": 0.02239,
      "decoded_frequency": 0.02195,
      "heldout_frequency": 0.022,
      "description": "7 letters + 1 digit"
    },
    {
      "template": "D8",
      "model_frequency": 0.02051,
      "decoded_frequency": 0.02105,
      "heldout_frequency": 0.0226,
      "description": "8 digits"
    },
    {
      "template": "L8D1",
      "model_frequency": 0.01285,
      "decoded_frequency": 0.01275,
      "heldout_frequency": 0.02025,
      "description": "8 letters + 1 digit"
    }
  ],
  "attack": {
    "kdf_profile": "demo",
    "entries_per_vault": 8,
    "wordlist": "attack/wordlists/demo_wordlist.txt",
    "wordlist_size": 629,
    "guesses": 500,
    "real_guess_index": 467,
    "conventional": {
      "cracked": true,
      "guess_index": 467,
      "elapsed_ms": 3973,
      "recovered_entries": 8,
      "recovered_entries_are_real": true
    },
    "honey": {
      "guesses_tried": 500,
      "elapsed_ms": 3827,
      "ms_per_guess": 7.65,
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
        "p50": 77.54,
        "p95": 93.3,
        "mean": 78.92,
        "min": 68.81,
        "max": 99.84
      },
      "unlock_ms": {
        "p50": 103.28,
        "p95": 132.69,
        "mean": 108.0,
        "min": 95.31,
        "max": 135.24
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
        "p50": 41.45,
        "p95": 49.08,
        "mean": 42.4,
        "min": 37.72,
        "max": 58.24
      },
      "unlock_ms": {
        "p50": 37.07,
        "p95": 40.79,
        "mean": 37.4,
        "min": 34.51,
        "max": 41.17
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
        "p50": 7.72,
        "p95": 8.1,
        "mean": 7.73,
        "min": 7.46,
        "max": 8.2
      },
      "unlock_ms": {
        "p50": 8.21,
        "p95": 8.68,
        "mean": 8.26,
        "min": 7.96,
        "max": 8.74
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
          "p50": 85.16,
          "p95": 101.83,
          "mean": 87.56,
          "min": 76.27,
          "max": 116.02
        },
        "wrong_ms": {
          "p50": 84.57,
          "p95": 105.2,
          "mean": 87.66,
          "min": 74.41,
          "max": 150.11
        },
        "ks_statistic": 0.08500000000000002,
        "ks_p_value": 0.46628639073563594,
        "same_distribution": true,
        "control_ks_p_value": 0.39352743357720954
      },
      "server_lite": {
        "right_ms": {
          "p50": 30.5,
          "p95": 37.11,
          "mean": 31.6,
          "min": 29.18,
          "max": 45.1
        },
        "wrong_ms": {
          "p50": 30.5,
          "p95": 36.64,
          "mean": 31.39,
          "min": 29.21,
          "max": 41.63
        },
        "ks_statistic": 0.12000000000000002,
        "ks_p_value": 0.11228360286766195,
        "same_distribution": true,
        "control_ks_p_value": 0.6284308022715471
      },
      "demo": {
        "right_ms": {
          "p50": 7.51,
          "p95": 8.34,
          "mean": 7.57,
          "min": 7.16,
          "max": 9.1
        },
        "wrong_ms": {
          "p50": 7.38,
          "p95": 8.11,
          "mean": 7.43,
          "min": 7.0,
          "max": 9.54
        },
        "ks_statistic": 0.31,
        "ks_p_value": 6.865581733487208e-09,
        "same_distribution": false,
        "control_ks_p_value": 0.7933622419382523
      }
    },
    "decode_only_us": {
      "rounds": 2000,
      "real_seeds": {
        "p50": 123.4,
        "p95": 188.31,
        "mean": 131.05,
        "min": 119.1,
        "max": 461.2
      },
      "random_seeds": {
        "p50": 67.8,
        "p95": 99.3,
        "mean": 71.26,
        "min": 55.9,
        "max": 244.4
      },
      "ks_p_value": 0.0
    }
  },
  "performance": {
    "unlock_p50_ms": 103.28,
    "unlock_p95_ms": 132.69,
    "target_p95_ms": 1500,
    "argon2_kdf_profile": "default (t=3, m=64 MiB, p=4)",
    "entries": 8,
    "measured": "in-process HoneyVault.unlock (no HTTP); see kdf for every profile"
  },
  "meta": {
    "git_commit": "516b425",
    "timestamp": "2026-10-17T08:30:07Z",
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
      "password_model": "pcfg-password-v2",
      "username_model": "pcfg-username-v1",
      "entry_seed_len": 532
    },
    "entry_dte_impl": "honeycore.dte.entry_dte.PCFGEntryDTE",
    "honeycore_impl": "real",
    "dataset_note": "passwords: RockYou rockyou-withcount, real counts (pcfg-password-v2); usernames: SecLists xato-net, Zipf-ranked (pcfg-username-v1)",
    "model_sha256": {
      "password_model": "8b225bb35d85624a2da1f4a3611574f2895336030660f2a838a63a3f159e76a6",
      "username_model": "ec5ffa2dfe40b0f469e8fe1ec74b37f67eb7b03e720edbe3abe9f89a57a26578"
    },
    "heldout_sha256": {
      "passwords": "c7bb2093aa39e0956e6a657de566325e667ea7bc809d43c122c5f78a792272ff",
      "usernames": "29355460e52169cd3310b863f8ce42f4dadaa4a2aa6b5df6de7a4b5f3dc46629"
    },
    "python": "3.12.10",
    "platform": "Windows-11",
    "step_seconds": {
      "round_trip": 4.28,
      "chi_squared": 16.94,
      "template_frequencies": 0.6,
      "classifier": 157.1,
      "attack": 8.14,
      "kdf": 5.72,
      "timing": 77.59
    },
    "duration_s": 271.38,
    "reproducibility": "held-out sampling, random seeds and CV folds use NumPy RNG(seed); decoys (model.sample), vault salts/nonces and the attack password use `secrets`, so classifier/attack numbers vary slightly between runs"
  }
};

export const evalHandlers = [
  // GET /api/eval/summary
  http.get('/api/eval/summary', () => {
    return HttpResponse.json<EvalSummaryResponse>(MOCK_EVAL_SUMMARY);
  }),
];
