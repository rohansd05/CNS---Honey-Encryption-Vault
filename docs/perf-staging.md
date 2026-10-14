# HoneyVault Staging API Latency Benchmark Report

**Date:** 2026-10-14  
**Environment:** Staging (`https://honeyvault-api.onrender.com`)  
**Deployment Platform:** Render Free Tier (Singapore)  
**Evaluator:** Tanmay (T5 — Utilities & Tooling)  
**Reviewer:** tanujb03 (T2 — Backend API)

---

## 1. Benchmark Execution

### Command
```bash
python -m scripts.bench_api --base-url https://honeyvault-api.onrender.com --runs 20 --out eval/results/api_latency.json
```

### Configuration & Pacing
- **Sample Count:** 20 iterations per measured operation (60 timed operations total)
- **Target URL:** `https://honeyvault-api.onrender.com`
- **Rate-Limit Pacing:**
  - Unlock interval delay: 2.5s (≤ 25 unlocks/min)
  - Login interval delay: 4.2s (≤ 15 logins/min)
- **Pre-flight Warm-up:** Bounded health check poll against `/api/health` until API and Honeychecker reported `ok`.
- **Failures:** 0 failures encountered across all 20 correct unlocks, 20 wrong unlocks, and 20 logins.

---

## 2. Environment & Crypto Parameters

- **Backend Impl:** `real` (HoneyVault PCFG + AES-256-CTR)
- **Honeychecker Status:** `ok`
- **KDF Profile:** `server_lite` (Argon2id: `time_cost=2`, `memory_cost_kib=19456`, `parallelism=1`, `hash_len=32`)
- **Cold-Start / Warm-Up Duration:** 0.71 s
- **Environment Limitations:** Render free tier (shared ~0.1 CPU, 512 MB RAM, Singapore region). Subject to cloud hypervisor CPU scheduling spikes and WAN jitter.

---

## 3. Measured Latency Results

| Operation | Mean (ms) | p50 (ms) | p95 (ms) | Max (ms) | Target p95 (s) | Status |
|---|---:|---:|---:|---:|---:|:---:|
| `unlock_correct` | 487.3 | 310.1 | 892.1 | 1820.5 | < 1.5 s | **PASS** |
| `unlock_wrong` | 399.8 | 273.2 | 954.2 | 1548.8 | < 1.5 s | **PASS** |
| `login` | 552.6 | 375.3 | 1317.5 | 2819.1 | N/A | – |

*Raw data recorded at `backend/eval/results/api_latency.json`.*

---

## 4. Analysis & Target Comparison

### 4.1 Target Assessment (PROJECT-BRIEF.md §11)
- **Normative Target:** "Performance: unlock p95 < 1.5 s on the deployed API (tune the KDF profile if needed)."
- **Measured Correct-Master Unlock p95:** **892.1 ms** (0.892 s)
- **Measured Wrong-Master Unlock p95:** **954.2 ms** (0.954 s)
- **Outcome:** **PASS**. Both correct-master and wrong-master operations satisfy the normative p95 latency threshold (< 1.5 s) on the deployed staging environment.
- **Maximum Outliers Note:**
  - `unlock_correct` maximum: **1820.5 ms** (exceeds 1.5 s by 320.5 ms).
  - `unlock_wrong` maximum: **1548.8 ms** (exceeds 1.5 s by 48.8 ms).
  - These isolated maximum spikes reflect occasional free-tier container throttling and network variability under Render's shared-CPU environment, while the 95th percentiles remain comfortably below the 1.5-second ceiling.

### 4.2 Behavior & Timing Observations
- Every wrong-master unlock request returned HTTP 200 with a well-formed decoy vault, preserving Honey Encryption Invariant 2 (no status code or response-shape distinction).
- On the measured sample ($N = 20$), both operations share a similar latency distribution (p50: 310.1 ms vs 273.2 ms; p95: 892.1 ms vs 954.2 ms).
- **Scope of Timing Observation:** While the macro-level latency distributions for right and wrong passwords align closely over WAN requests on staging, these measurements reflect end-to-end network observations and do not mathematically prove the absence of subtle cryptographic timing-channel or side-channel leakage.
