---
name: reference_accord_gp6c2c_real_distribution_overflow_wall_not_binding
description: gp-0x6c2c is not on any CAN427 wire probe, but its real distribution can be reconstructed from real rate_c telemetry via frequency-domain filtering (FFT * exact H(f) * IFFT), validated against the true 1kHz integer recurrence to 0.002%. Real max observed (~5,141-5,320 counts, r97+ra4 corpus) sits 3.3-6x BELOW the int32-overflow threshold at x3.0 dose (17,068) and the structural producer ceiling (32,000) -- the overflow wall does NOT bind in practice. Also corrects an earlier same-session clamp-crossing-fraction estimate that used a single-frequency sinusoidal-peak proxy and overestimated by 3-130x; the FFT-validated numbers are 0.088%/1.563%/9.969% in-burst clamp-crossing at x1.5/x2.0/x3.0 on V104.
metadata:
  type: reference
---

# `gp-0x6c2c` real distribution, reconstructed from telemetry — the overflow wall is not binding

2026-08-22, `dynamics-designer` task (team-lead: "size [the gp-0x6b26 raise] against the overflow
wall... measure gp-0x6c2c's real distribution... this is the highest-value number you can get me").

## Method — frequency-domain filtering, validated against ground truth [EVIDENCE]
`gp-0x6c2c` is not on any CAN427 probe in any build found. Reconstructed it from real `rate_c` (true
column deg/s, `ra4`/`r97` caches) by: FFT the real signal → multiply by the exact confirmed z-domain
`H(f) = 64·H1(f)·(1−z⁻¹)·H2(f)` (a1=37/128, a2=22/64, evaluated as a continuous function of f, valid
up to the 1kHz Nyquist) → IFFT. This correctly weights each frequency component of the REAL signal by
its own true gain — unlike treating an instantaneous sample as a sinusoidal peak (see the correction
below).

**Validated**: fed a synthetic 26Hz tone through (1) this FFT method at the cache's ~101Hz rate and
(2) a direct Python mirror of the true 1kHz integer recurrence. Results: 8801.2 vs 8801.4 (0.002%
apart) — method confirmed sound. Caveat: content above the cache's own ~50Hz Nyquist is invisible to
this reconstruction; for the 18-30Hz question this is not a material limit.

## Result — real driving never approaches the overflow wall [EVIDENCE]
```
V104 (ra4), reconstructed |gp-0x6c2c|, engaged <16km/h: p50=119 p90=1064 p95=1296 p99=1704 p99.9=2053 MAX=5141
STOCK (r97):                                            p50=25  p90=66   p95=110  p99=201  p99.9=396  MAX=5320
Structural producer ceiling (from the KNOWN ±0xfa0000 clamp on the pre-EMA difference, propagated
  through the EMA and >>9): 32,000 -- PROVABLE, not just empirical (EMA output magnitude <= max input
  magnitude, standard convexity property; 16,384,000/512=32,000 exactly).
Int32-overflow threshold at K=Y (503,342,400/Y): x1.5=34,138 x2.0=25,602 x3.0=17,068
```
**Zero frames observed anywhere near the overflow threshold, at any K up to x3.0, in either arm.** The
observed max (~5,141-5,320) sits 3.3x below the x3.0 threshold and 6x below the structural ceiling.
Caveat: bounded by corpus size — a rarer/more extreme event outside `r97`/`ra4` isn't ruled out, but
there is no evidence anywhere close to the wall in real driving, including inside V104's own bursts.

## 🛑 SELF-CORRECTION — the earlier same-session clamp-crossing estimate was inflated 3-130x
Original method (same session, earlier): compared each instantaneous `rate_c` SAMPLE directly against
a threshold computed as if that sample were the peak of a SUSTAINED 26Hz oscillation of the same size.
Real signal energy is dominated by lower-frequency content, which this cascade passes at much lower
gain (|H(3Hz)|=1.2 vs |H(26Hz)|=8.8) than the single-frequency proxy assumed.
```
                    single-frequency proxy (WRONG, superseded)   FFT-reconstruction (CORRECT)
x1.5 (current):     11.62%                                       0.088%
x2.0:                17.40%                                       1.563%
x3.0:                27.52%                                       9.969%
```
⇒ The saturating-clamp/limit-cycle mechanism (candidate A2 hypothesis) has LESS empirical support than
first reported — real clamp engagement is smaller (~10% at x3, not ~27%), though still real and
dose-scaling.

## Shadow-lockstep consequence, traced one hop further [EVIDENCE, fresh decompile]
`FUN_0006b9fa`→`FUN_0006ce7c(4)` writes a byte pair (`gp-0x444f`/`gp-0x4e53`) read by exactly one
function, `FUN_0006ce90` (confirmed via `search_instructions`, both offsets, 5+3 raw hits, single
reader). On mismatch it calls `FUN_0005bb04(8)` — decompiled fresh: a plain SATURATING OCCURRENCE
COUNTER (`count[8]=min(count[8]+1, INT16_MAX)`, no fault call inside). This is a DEBOUNCED, SHARED
monitor slot (index 8) — the same sink every one of the ECU's 6+ shadow-lockstep pairs feeds into
(per [[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]]'s census). NOT an instant hard
fault. Final hop (what a CONFIRMED state-8 read eventually does — degrade assist or not) not traced;
flagged open. Given this mechanism is already live and shared across 6+ pairs on every build in this
kit's history with zero reported nuisance faults, and (a) shows overflow essentially never occurs even
at x3, residual risk here is second-order.

## Build proposal that used this — x3.0 stock-relative Y-table raise
```
mode26  0xD7A5C-0xD7A61  int16[3]  stock (-9830,-5734,-1966)  current (-14745,-8601,-2949)  -> (-29490,-17202,-5898)
mode27  0xD7A6C-0xD7A71  int16[3]  same triple, same edit
```
Predicted in-burst clamp-crossing fraction at this dose: ~9.97% (V104 corpus). `0xC407E` clamp stays
511, unchanged (structurally decouples from DTC-0x1d at any multiplier, prior session).

## Related
[[reference_accord_gp6b26_v106_transfer_function_correction_and_disqualification]] (the file this
extends), [[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]] (the GATE-1 census this
shadow-lockstep trace extends one hop further).
