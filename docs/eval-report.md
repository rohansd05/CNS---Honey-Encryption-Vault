# Evaluation report

> Owner: T1 (Nidhi, Dhruv). Placeholder — filled in Phase 3 from `backend/eval/results/latest.json`
> (`python -m eval.run_all`). Metrics are defined in PROJECT-BRIEF.md §11. Report results honestly,
> whatever the numbers.

## 1. Setup
_TBD: corpus, train/held-out split, model sizes, KDF profiles, hardware._

## 2. Round-trip & totality
_TBD: `decode(encode(x)) == x` rate (target 100%); decode totality on random seeds._

## 3. Chi-squared tests
_TBD: (a) seed int uniformity on held-out passwords (expect p > 0.05); (b) decoded template
frequencies vs model._

## 4. Distinguisher
_TBD: logistic regression + random forest, 5-fold CV, real vs decoy (target ≤ 60%, ideal 50%)._

## 5. Attack comparison
_TBD: guesses to crack the baseline vs honey vault behaviour; distinct vaults per guess._

## 6. Performance
_TBD: unlock p50/p95 per KDF profile, local and on Render (target p95 < 1.5 s)._

## 7. Limitations
_TBD._
