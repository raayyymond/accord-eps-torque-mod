# V295 "plant" agent — FAIL / surprise criteria, written 2026-09-30 BEFORE any plant number was computed

Only the brief, the handoffs, the attribution report and the loader docstring had been read when this was written.
No fit, spectrum or simulation had been run on route `75604b0a432fdc89_00000071--a7b8ba5d9d` by this agent.

## Instrument / data gates (a failure voids what depends on it)
- **G1 torque reconstruction.** The byte-exact 1 kHz live march (FF + trim, V294 cells) sampled at the tap instants
  must match the 50 Hz tap to rms ≤ 10 counts on hands-off engaged frames (the attribution read 5.4). If it does not,
  the 100 Hz torque series built from it is NOT used above 25 Hz, and every >25 Hz statement is withdrawn.
- **G2 unit spot check.** `x_fw/8` vs `d(0x14A angle)/dt` must agree to 2 % (slope) on engaged frames; the angle and rate
  must be the same physical quantity or J/b/k mix units.
- **G3 estimator controls.** (a) IV and OLS run on a SIMULATED closed loop (known J, b, k, F, the byte-exact trim, a
  coloured road disturbance, the route's own command) must recover J, b, k within 15 % for IV. If IV cannot recover a
  known plant in simulation, the drive IV numbers are BELIEF only. (b) A zero-lag control in the FRF: the IV transfer
  from T_ff to the FF part of the modelled T must read unit gain / 0° (checks the alignment of the two series).

## FAIL criteria (the plant is "not ready" if any fires)
- **F1** No speed band gives a mode (f_n, ζ) with a bootstrap CI narrower than ±50 % on J — i.e. inertia is not
  identifiable from this drive at all.
- **F2** IV and the frequency-domain fit disagree on J or k by more than a factor 2 in the two best-powered bands
  (5–10, 10–15 m/s) — the two methods do not describe the same plant.
- **F3** The measured trim (T_tap − FF·taper) disagrees with the byte-exact model by > 20 % in gain or > 20° in phase
  anywhere in 0.5–5 Hz where coherence ≥ 0.5 — the 1 kHz model the design will rely on is not validated.
- **F4** The validation replay (route command → byte-exact PID → plant, held-out segments) gives angle R² < 0.5 or
  rate R² < 0.3 in a band that holds ≥ 60 s of hands-off engaged data — that plant is NOT ready for that band.
- **F5** The replay is unstable/divergent for any member of the delivered family (nominal + CI corners + light-b)
  under the SHIPPED V294 cells — the family contradicts the drive (V294 flew without faults).

## Surprises (report loudly, not FAILs)
- **S1** The identified J differs from the prior 8e-5 u/(deg/s²) (= 0.21 T counts/(deg/s²) at 2625.4 T per u) by more
  than ×2 — the design's K_α/J = 1 premise moves.
- **S2** ζ_open at the wheel mode < 0.1 or > 0.7 in any band.
- **S3** The fb clamp (|r26| = 1024) binds on > 0.1 % of engaged frames.
- **S4** A coherent (≥ 0.5) line appears in 13–17 Hz or 18–22 Hz in T→rate, or the rate spectrum shows a narrow peak
  there while engaged hands-off.
- **S5** The trim's rms exceeds 25 % of the FF rms in any band in normal (hands-off) driving.
- **S6** OLS and IV differ by more than 30 % on J (the trim-induced bias is large).
