---
name: feedback-validate-the-pre-registered-instrument-on-a-real-null-route-before-the-drive
description: "PROCESS 2026-09-23 (V294 redo): a pre-registered within-drive regression must be RUN ON A REAL NULL ROUTE (a build where the term is provably zero) with a synthetic-live positive control BEFORE the drive, and its regressor's SIGN must be calibrated on the same route — V294's rule as first written read 'live-like' on V293's null routes, had the wrong units, and would have called a correct build 'inverted' on the kit's raw 0x18F rate column (= −8 × carState rate)."
metadata:
  type: feedback
---

# Validate the pre-registered instrument on a real null route before the drive (2026-09-23)

V294's page pre-registered "regress residual on −(0x18F rate, 2 Hz LPF, differenced); slope > 0 = live,
positive correlation = inverted → revert". Replayed by a fresh auditor on twenty 20 s hands-off windows of the
V293 routes 70–75 (V293 forces r26 = 0, a true null) it read **+0.021 (−0.027 … +0.087)**, overlapping a live
reading (+0.067); a ±5 % feedforward-gain error alone moves it ±0.05 and can flip a null to "inverted". The
units were wrong (1.85 is |T/rate| at 2.4 Hz, not a slope on a differenced signal), and the kit's v280 cache
`rate` column is the RAW 0x18F field = −8 × carState.steeringRateDeg, so on that column a correct build would
have triggered a false revert.

**Why:** the static surface predictor ignores the 5 Hz output lag, so the null residual is a filtered copy of the
command — which drives the wheel. Any regressor built from the wheel's motion then correlates with it.

**How to apply — every pre-registration, before the drive:**
1. Run the estimator exactly as written on a REAL null route (a flown build where the term is provably zero).
2. Add a synthetic-live positive control (the term computed by the byte-exact chain from the route's own signals,
   injected into the real tap) and require the two distributions to separate with a stated threshold.
3. Match the chain's own dynamics in the predictor and the regressor (output lag, fade, ms alignment) and add
   the feedforward and its derivative as nuisance terms.
4. Calibrate the regressor's SIGN on the same route (the high-passed feedforward torque must correlate
   positively with the wheel acceleration in the chosen column's convention); prefer carState.steeringRateDeg.
For V294 the fixed rule is β > +0.10 T counts per deg/s² = live (expected +0.21), |β| < 0.04 = null, 20/20 each arm.

Related: [[accord-v294-acceleration-trim-on-the-v293-torque-map-built]] · [[feedback-attribute-the-build-from-the-tap-not-from-the-label]] · [[accord-cereal-slot-137-collision-and-tap-polarity-plus]]
