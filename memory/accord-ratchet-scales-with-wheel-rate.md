---
name: accord-ratchet-scales-with-wheel-rate
description: The operator's own symptom axis is STEERING-WHEEL RATE, not vehicle speed; engagement's 6-9 Hz amplification grows with it, and the mode is strongly damped by driver grip.
metadata:
  type: project
---

**Operator, 2026-08-09 — the sentence that gave the two symptoms an axis:**
> *"micro-ratcheting and ratcheting when LKAS is engaged and spinning the wheel **at all**
> (micro-ratcheting) and **quickly** (ratcheting), respectively. Macro-ratcheting is on **large
> steering angle transients**."*

Every ratchet measurement in this kit had been stratified by **vehicle speed**. The two axes are
strongly anti-correlated in the corpus — **corr(log |rate|, log speed) = −0.640** engaged — because
you spin the wheel in a car park, not at 116 km/h.

## What is EVIDENCE
`analysis-2020accord/v89_a5_engagement_model.py`, 400 windows / 12 routes / 93 episode blocks,
`log e_band ~ route + eng + eng×log|rate| + log|rate| + log v + log hands`:

| term | 6–9 Hz | 32–38 Hz control | contrast |
|---|---|---|---|
| `eng × log rate` | **+0.313 [+0.103, +0.490]** | +0.168 [+0.064, +0.260] | +0.144 [−0.004, +0.267] |
| `log hands` | **−0.720 [−0.918, −0.500]** | −0.216 [−0.326, −0.104] | **DISJOINT** |

- **Engagement's amplification of the 6–9 Hz column mode GROWS with wheel rate**: engaged/manual
  **1.16× at 2 deg/s → 1.92× at 10 → 3.94× [2.19, 6.70] at 100 deg/s.** First instrument in the kit
  that responds to the operator's micro-vs-ratcheting distinction at all.
- ★★ **The mode is strongly damped by DRIVER GRIP, band-specifically** (CIs disjoint). This is the
  session's most solid result and it says what class of lever could work: something that adds
  damping at the column at 6–9 Hz, i.e. emulating the operator's own hands.

## What is BELIEF, and what is NOT claimed
🛑 **That the rate dependence is RATCHET-SPECIFIC is NOT established.** The 32–38 Hz control band
does the same thing at about half the rate and the contrast's lower bound is **−0.004**.
🛑 **D5's "amplitude decays 4.8× creep→highway" is partly a RATE effect read as a SPEED effect** —
its creep stratum's median |rate| is 13 deg/s vs the highway stratum's 1 deg/s. **The FREQUENCY
result is untouched**: `f0 = +0.0102·v + 7.998 Hz` stands (see [[accord-v88-flew-grinding-fixed-command-intact]]).
🛑 **Micro and macro could NOT be separated** — `corr(log |rate|, log angle-ptp) = +0.857` on route
73; the axes are collinear and both slopes straddle zero.

## Two traps this produced, both caught by controls
1. **Per-band order vetoes build DIFFERENT window sets per band** and manufacture band-specificity
   out of nothing (`v89_a1` read +0.490 vs +0.039; on matched windows it is +0.492 / +0.385 / +0.400).
   **Veto once on a common band, then compare bands on identical windows.**
2. **`_cache_r66` and `_cache_r66x` are the SAME route.** Globbing `_cache_r*/r*.npz` double-counts
   it, and that alone moved the headline contrast from +0.172 [+0.038, +0.288] (excludes 0) to
   +0.144 [−0.004, +0.267] (does not). **Glob by ROUTE, and re-run the headline after any loader
   change.**

⊕ Also dropped: `cmd → column` coherence is not an attribution instrument — `gp-0x6b98` carries base
assist, which is a function of column torque, so its 6–9 Hz coherence reads **0.254 engaged but
0.544 MANUAL**. Loop feedthrough, not attribution.

See [[accord-base-assist-damper-cannot-reach-the-micro-regime]] and
[[accord-leverb-rate-discriminator-underpowered]].
