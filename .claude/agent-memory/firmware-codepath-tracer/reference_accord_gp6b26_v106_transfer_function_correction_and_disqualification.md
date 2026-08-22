---
name: reference_accord_gp6b26_v106_transfer_function_correction_and_disqualification
description: gp-0x6c2c/gp-0x6b26's cascade gain 26Hz-vs-4.3Hz ratio is 5.1x, NOT the ~36x a pure double-differentiator (omega^2) predicts. REDUCING gp-0x6b26 below x1.5 is DISQUALIFIED (V94 on-car abort). RAISING it toward x2/x3 is UNTESTED at 21-28Hz, NOT closed -- the prior "closed both directions" verdict over-reached a confounded dose-check; see the ADDENDUM. Real telemetry: the clamp binds 11.6%/17.4%/27.5% of in-burst frames at x1.5/x2/x3 -- partial support for a saturating-damper limit-cycle mechanism, not proof of it. Also: int32-overflow ceiling at x2+, current on-car state (x1.5, frozen V96-V105).
metadata:
  type: reference
---

# `gp-0x6b26` re-examined for V106 (26 Hz stability-margin task) — TF corrected, DISQUALIFIED as a reduce-lever

2026-08-22, `dynamics-designer` task (team-lead brief: rank candidates for buying 18-30Hz gain margin
at 6x torque). Extends [[reference_accord_gp6b26_closed_both_directions_v94_aborted]] and
[[accord-gp6b26-is-inertia-not-damping]] (project memory) — does not supersede either, adds a
transfer-function correction and a V106-specific verdict.

## Current on-car state [EVIDENCE — fresh Python LE byte read, stock through V105]
`0xC407E` (gp-0x6b26's own output clamp) = **511 on every build stock→V105**, untouched since V81
reverted it. `gp-0x6b26` Y-table (engaged modes 26/27, anchor point) = stock `-9830` → **`-14745`
(exactly x1.5) on every build V96 through V105**, frozen ≥10 sampled builds. This is the V91/V92-era
raise; it has never been reverted and is on V104 (the car right now) and unflashed V105.

## Structure reconfirmed fresh [EVIDENCE — decompile this session, `FUN_00041464`@0x41464,
`FUN_00036c12`@0x36c12, `FUN_0003aa2c`@0x3aa2c, program=code.bin; matches
[[accord-gp6b26-is-inertia-not-damping]] to the instruction]
`gp-0x6c2c` = EMA2(32×[EMA1(rate<<10)[n]−EMA1(rate<<10)[n−1]], α2=cal 0xC40DC=22/64)>>9,
α1=cal 0xC643C=37/128, fs=1000Hz — angular ACCELERATION. `gp-0x6b26 = clamp(((gate(gp-0x6c2c)·Y_speed
(cal 0xCBE74 LERP, X=gp-0x6a5e speed))>>6)·0x111>>18, ±cal(0xC407E))`, Y_speed always negative.
Aggregator adds it directly, unweighted (+1), always-passing gate (its own ±511 clamp never reaches
the aggregator gate's ±1024 reject window) at `0x3ac98`, sibling to `gp-0x6ad4`/`6bbe`/`6bd0`/`6b86`/r24/r26.

## 🛑 TRANSFER-FUNCTION CORRECTION — 5.1x, not ~36x
`H(f) = 64·H1(f)·(1−z⁻¹)·H2(f)`, H1/H2 single-pole EMAs at a1=37/128, a2=22/64, fs=1000Hz (Python
mirror of the exact integer cascade, cross-checked against [[reference_accord_gp6b26_friction_lane_damping_candidate]]'s
independent derivation to 3-4 sig figs):
```
f(Hz)   |H|     phase
3.00    1.20    84.8°
4.30    1.72    82.5°
7.79    3.08    76.4°
21.90   7.49    54.9°   (f0 @1x)
24.90   8.54    48.9°   (f0 @6x)
25.50   8.68    48.0°
26.00   8.80    47.3°
```
**|H(26)|/|H(4.3)| = 5.12×** — a naive pure-double-differentiator (ω²) estimate gives (26/4.3)²≈36.6×,
which OVER-PREDICTS by ~7×. The two EMA poles roll the cascade off well before 26Hz, so growth is
sub-quadratic. Real, but much more modest frequency-selectivity than an ω²-argument assumes — flag
this before using gp-0x6c2c/gp-0x6b26 as a "nearly-free-at-low-f, strong-at-high-f" argument for ANY
future lever, not just this one.

## 🛑🛑 WHY "REDUCE IT" IS DISQUALIFIED FOR V106, NOT MERELY UNTESTED — three converging lines
1. Isolated-stage phase (this term vs its own producer) stays nominally dissipative-signed (cos>0) at
   every checked frequency — the naive reading.
2. **But the CLOSED-LOOP measurement (V96, same x1.5 dose now on the car) contradicts the naive
   "zero real part, pure inertia" reading**: phase vs WHEEL rate measured +137°/+139° (two drives) ⇒
   **+518/+565 counts of REAL positive damping at 6-9Hz**, not the 90°-quadrature reactive term
   isolated analysis predicts. Per [[reference_accord_gp6b26_closed_both_directions_v94_aborted]]:
   *"isolated-stage phase/DC analysis of a term that feeds a real closed loop is not sufficient — phase
   accumulates around the loop in a way a single-stage transfer function does not capture."*
3. **A z-domain dissipative-fraction table (same cascade, from
   [[reference_accord_gp6b26_dtc1d_decoupled_from_dose_and_path1_discovered]]) says this term's
   dissipative fraction is HIGHER at the grind band than the ratchet band**: 23.5% dissipative at
   7.79Hz vs **58-72% dissipative at 21.09-28.1Hz**. If it's a real damper at 6-9Hz, structurally it is
   MORE of a damper at 21-28Hz, not less.
4. **The on-car test of "lower it" already ran**: V93/V94 (mode24 x0.50, modes26/27 x0.25, fallback
   x0.75), route `7d`, fault-free. Operator: *"made the stuttering and grinding worse, by a lot. So much
   so that it vibrated the entire car, and I decided it was not safe to drive."* Grinding is one of
   V106's two target symptoms.

⇒ This term currently reads as a NET STABILIZER at the grind band, not a margin-eater. Reducing it is
a repeat of an already-flown, already-worse, already-aborted lever — not a fresh idea.

## New this session — a candidate PARTIAL mechanism for the mode's own amplitude-dependence [mixed]
At fixed rate amplitude, gp-0x6b26's own ±511 clamp is reached **~7.3× sooner (lower amplitude) at
26Hz than at 3Hz** (direct consequence of the |H| ratio above — EVIDENCE). Via the inherited (not
re-verified this session) 4.7121 ct/(°/s) scale: clamp-crossing ≈ **51°/s at 26Hz** (current x1.5 K) vs
**≈365°/s at 3Hz**. The measured median 21-28Hz rate in the worst band (15-40°/s, V104 6×) is 20.79°/s
— BELOW that crossing, so this does NOT explain the median, only the amplitude tail (p90+).
BELIEF-grade: amplitude-dependent self-limiting at the tail, not the whole nonlinearity story.

## What remains open, NOT disqualified
The FLAT Y-table raise/lower is closed. A FREQUENCY-SHAPED intervention on this same already-isolated,
low-blast-radius signal (`gp-0x6c2c`) — e.g. narrowing clamp headroom specifically, or a cave reshaping
only its >15Hz content — is structurally different and not ruled out by this record, but was not
designed this session.

## 🛑🛑 ADDENDUM (same session, team-lead pushback) — the RAISE direction is UNTESTED at 21-28Hz, NOT
closed. Retracting part of "DISQUALIFIED" above.

Team-lead challenged the inherited "closed both directions" verdict, correctly. Re-reading
[[reference_accord_gp6b26_closed_both_directions_v94_aborted]]'s OWN citation for the up-direction:
"up is measured inert" rests on ONE check — "engaged stratified ratio 0.99 [0.91,1.26] vs
pre-registered 1.50" — a **DOSE-VERIFICATION check** (did CAN427 see the expected 1.5x jump), explicitly
flagged in that same memory as **confounded** (RULE 7). It is NOT a 21-28Hz symptom-band measurement.
The only real closed-loop measurement of the x1.5 dose (V96's +518/+565ct Re(Z)) is **at 6-9Hz**. The
"58-72% dissipative at 21.09-28.1Hz" figure this file's own §3 above uses is a z-domain THEORETICAL
extrapolation of the isolated cascade's phase formula — not an on-car measurement at that band, and
isolated-stage analysis is exactly what §2 above says is insufficient for a term in a real closed loop.
**I used an isolated-stage theoretical claim to argue against re-testing the raise direction — the same
category of error this file's own §2 warns about.**

⇒ **CORRECTED VERDICT: the raise direction beyond x1.5 (toward x2 or x3, stock-relative) is UNTESTED at
21-28Hz, not falsified, not closed.** It is NOT contradicted by V94's abort (that tested REDUCING) or by
the 6-9Hz Re(Z) result (different band). §4's "already-flown, already-worse, already-aborted" framing
applies ONLY to the DOWN direction — restating precisely: **DOWN is disqualified (V93/V94, on-car,
symptom got worse). UP is untested at this band**, and per
[[reference_accord_gp6b26_closed_both_directions_v94_aborted]]'s own "do not move it either way without
a fundamentally different plan" caution — a plain further Y-table raise IS arguably that different plan
relative to what V94 tried (opposite direction), so the caution does not automatically extend to it.

### What breaks at x2/x3 (stock-relative — cross-validates ADDENDUM 2 of
[[reference_accord_gp6b26_dtc1d_decoupled_from_dose_and_path1_discovered]] almost exactly: my fresh
503,342,400/Y overflow-threshold recompute gives 25,603/17,069 vs that memory's cited 25,607/17,072)
```
Y=14745 (x1.5, current): int32-overflow threshold=34,138  (gp-0x6c2c producer ceiling ~32,000 -- SAFE)
Y=19660 (x2.0):           threshold=25,603  (BELOW ~32,000 -- overflow becomes structurally REACHABLE)
Y=29490 (x3.0):           threshold=17,069  (well below -- reachable more often)
clamp-crossing rate @26Hz: x1.5=51.35 deg/s, x2.0=38.51 deg/s, x3.0=25.68 deg/s (inherited 4.7121ct/(°/s) axis)
```
Consequence of overflow (per the cited memory): corrupted value wraps arbitrarily for one tick before
the ±511 clamp runs; likely caught by the `gp-0x4cd0` shadow-lockstep (single-tick, no persistent
state) but not proven zero-risk. x2+ needs a headroom check or a pre-clamp on the intermediate product,
not avoidance outright.

### In-burst clamp-crossing fraction — REAL TELEMETRY, `ra4`/`r97` caches, this session
Reused `ra4_burst_conditional.py`'s Schmitt-triggered 21-28Hz analytic-envelope burst detector
(engaged `cc_lat>0.5`, <16km/h) but on `rate_c` (true deg/s) throughout for axis consistency. Duty
reproduces the pre-registered result closely (0.918 here vs 0.933 reported — methodology check passes).
```
V104 (ra4) IN-BURST |rate_c| (10,456 frames): p50=10.0 p90=60.0 p95=132.0 p99=206.0 max=254.0 deg/s
fraction of IN-BURST frames >= clamp crossing:  x1.5=11.62%   x2.0=17.40%   x3.0=27.52%
```
**The clamp DOES bind on a real, non-trivial, DOSE-SCALING fraction of burst frames** — corrects my
own §5 above, which used the unconditional MEDIAN (below crossing) and concluded "tail only, does not
explain the median." The in-burst-conditional picture is materially different. **Still not the majority
even at x3 (~72% of burst frames remain unclamped)** — PARTIAL support for a saturating-damper limit-
cycle mechanism, not proof it is the sole/dominant one. Caveats: no shuffled-null control run this pass
(time-boxed simplification, not the full pre-registered replication); crossing arithmetic assumes each
`rate_c` sample is a clean sinusoidal-peak proxy for the steady-state 26Hz condition; 4.7121 ct/(°/s)
axis identity is inherited, not re-derived this session (flagged BELIEF-grade elsewhere in the kit too).

## Related
[[reference_accord_gp6b26_closed_both_directions_v94_aborted]], [[accord-gp6b26-is-inertia-not-damping]]
(project memory), [[reference_accord_gp6b26_friction_lane_damping_candidate]],
[[reference_accord_gp6b26_dtc1d_decoupled_from_dose_and_path1_discovered]],
[[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]] (sibling session's fresh GATE-1 census
on the same producer, same day — cross-check before any cave-shaped follow-up).
