# The actuator ALREADY rails below 8 m/s on the flown config — 0.65 s, 16 episodes, all at large angle

**Measured 2026-09-19** on 9 torque-mode routes (revs 2→6.4, 5.0 ks engaged hands-off), each reconstructed with
the fork tables at its own flown commit. Files: `rlog-tools/studies/v282-reference/ffgain_ceiling/`
(`ffrecon.py`, `sweep.py`, `SWEEP-OUT.txt`, `zout.py`, `ZOUT-OUT.txt`).

Reconstruction positive control: the whole `ff_torque` rebuilt at each route's flown gain vs logged `pid_log.f/LAF`
— corr 0.9990–1.0000, slope 0.995–1.002, rms 0.0003–0.0058 torque on 7 routes. Instrument identity
`pid_log.output == -clip(p+i+f, ±LAF)/LAF` holds to 6e-8 on all 10 routes, so **full scale is `|output| = 1.0`**
(`steer_max`, `latcontrol.py:17`). `latAccelOffset` must be OFF in the reconstruction.

## The finding

At the flown `AccordFFRateGain = 0.5`, below 8 m/s (1027 s):

- **16 clip episodes, 0.650 s total**, longest **0.100 s**, p90 duration 0.080 s, max |TOT| 1.321.
- **98–100% of episodes sit at |wheel angle| > 30 deg, median 166–300 deg** — large-angle low-speed transients,
  the regime the operator calls *jerky, not smooth and gradual* and *medium-to-large angle rate transients not
  handled well*.
- At the 65 railing frames the **FEEDFORWARD carries 1.00–1.05 of the command** while P carries 0.11–0.13 and I
  0.02–0.03. The hold map alone contributes 0.60–0.62 near lock at 2.0–2.4 m/s. The move term has the same sign as
  the command at **100%** of them, so more gain pushes further INTO the rail, never out.
- For each episode's duration the delivered command is pinned: **the output stops being a function of demand or
  error (loop open), and the feedforward stops being proportional to demand exactly when demand is largest.**

Headroom `1 − |TOT|` is ≥ +0.17 in every angle bin below 120 deg and **negative in every bin above it**, where 56
of the 59 co-signed rail frames live.

## What it kills

- **`AccordFFRateGain` as a lever.** Ceiling below 8 m/s is **0.60** (criterion |FF| ≤ 1.0); 0.85 excluding
  near-lock; 2.15 only if you exclude near-lock AND accept a per-route median instead of worst case. The toggle is
  clamped at **max 1.5** in both `starpilot_variables.py:825` and `device_settings_layout.json`, so 2.0 was never
  reachable. At 8–15 m/s the ceiling is 2.9–3.5 and **nothing rails at any gain** — the raise had been proposed in
  the one band that cannot take it. Gating it below 8 m/s does not help and a STEP in the gain at 8 m/s injects its
  own transient (0.34 torque at 100 deg/s with g = 2.0), so it would have to be speed-interpolated.
- 🛑 **Since 0.5 already rails, there is no gain ≥ 0.5 that keeps the total under full scale below 8 m/s.**
  0.5 is the largest that does not make it worse.
- **Any additive term that is at full value at large angle.** A candidate one-sided +0.020 outward term sat at
  `0.02000` exactly on 62 of the 65 railing frames, co-signed 95.4%, and converted **every one of the 16 frames
  within one dose of the rail** into a railed frame — while delivering **exactly 0.000** of realised torque there,
  because the command is already at ±1.0. Cost curve: rail seconds 0.650 → 0.740 at level 0.015 (durations
  unchanged) → 0.810 at 0.020 (longest 0.110 s, p90 +19%). The 0.015→0.020 step is +0.070 s against the previous
  step's +0.010 — **a knee at 0.015.** No level adds zero railing; the cost is continuous from zero.

## 🛑 Traps recorded

1. **Never clear an authority claim with a pooled p99.** A design cleared its +0.020 with "p99 |cmd| 0.4275 +
   0.020 = 0.4475, no clamp reached". p99 over all engaged frames is dominated by the 93–99% that are dwells at
   speed. **For a term gated to low speed, the claim must be made on the LOW-SPEED MAX.**
2. **A gain sized at dwells says nothing about the rail.** At 2–8 m/s, dwell frames (<15 deg/s, 70% of the band)
   move max |FF| 0.642 → 0.676 for a **4x** gain change, while the 7.2% of frames above 75 deg/s go 0.932 → 1.620
   and rail seconds go 0.62 → 4.23. The whole effect of the lever lands on the frames already nearest the rail.
3. **`tanh(angle/1.0 deg)` is not a taper.** It is 1.000 flat from ~4 deg to 400 deg, so it is equally maximal at
   5 deg (headroom +0.234) and at 300 deg (negative headroom). Re-tuning that scale cannot add a large-angle taper;
   a taper must be a NEW factor. Keying it on realised headroom `1 − |cmd|` would work but **forfeits the
   "no measurement, no loop gain" safety property** — `cmd` carries P and I, and this kit has falsified a friction
   relay for self-excitation twice (route 71's 2.34 Hz limit cycle, route 73's 4–4.7 Hz chatter).
4. **Two record corrections found on the way.** Route 70 flew **`AccordRatePlantFF = 0`** — the plant feedforward
   never ran on that drive, so anything derived from it is an offline recomputation, not a delivered command. And
   the fork comment at `latcontrol_vehicle_tunes.py:179-183` (the "max 1.13 at gain 1.0" sentence) reproduces to
   **+0.4%** but describes the low-speed hold knots **as they were before the same commit cut them** to
   `[0.30, 1.00, …]`; with the shipped table the identical sum gives 0.899 and 0.00 s over full scale. The
   sentence's arithmetic is sound and its tables are stale — **do not use it as an oracle.**

Related: [[accord-lowspeed-hold-ff-is-missing-an-additive-intercept-not-a-stiffness]] ·
[[accord-v293-flew-route70-plant-is-a-spring-ratchet-measured]] ·
[[accord-torque-mode-loop-delay-is-55-75ms-and-xcorr-cannot-measure-it]]
