---
name: reference-accord-v48c-gate2-notch-stable-brick-was-ram
description: GATE 2 (closed-loop stability) analysis done for the V48C notch revival — the check V48B skipped. Inserting the ACTUAL notch biquad into a calibrated base-assist loop model (Nyquist / magnitude+phase, not a single-frequency magnitude) shows the V48B notch as a PURE FILTER is closed-loop STABLE and IMPROVES the margin (|1-L|min 0.139→0.400, hard edge 4.66×→6.67×). => the violent V48B brick is attributable to the RAM collision (Gate 1), not to closed-loop instability of the notch. A Q2 −8 dB notch is strictly better than V48B's Q5 (poles r=0.948 vs 0.979, worstRe 0.42 vs 0.60, edge 9.6×) at the same depth and negligible feel cost. Script: analysis-2020accord/eps_v48c_gate2_closed_loop.py.
metadata:
  type: reference
---

# V48C Gate 2 — the notch itself is closed-loop stable; the V48B brick was the RAM collision

`analysis-2020accord/eps_v48c_gate2_closed_loop.py` (pure stdlib; reuses the calibrated loop-gain model
`eps_loop_gain_model.py` — MEASURED f0=21.4 Hz, Q(4x)=13.6, anchor |L(4x,w0)|=0.875, zeta_bare=0.294).
It builds the base-assist open loop L(jw)=m·k·(s/w0)·P(s)·e^{−s·td} (rate carrier through a 2nd-order
resonance, ~1.5-sample loop delay), inserts a candidate filter in the FEEDBACK path (L_filt = N·L,
because the filter sits on gp-0x4f60 before the collocated carriers read it), and runs a full
Nyquist / gain+phase-margin scan (positive-feedback convention: critical point +1; stable iff no
positive-real-axis crossing with Re≥1 and no encirclement). This is the exact check V48B skipped —
it had inserted only the single-frequency magnitude |N(21.4)| into the *LKAS* model.

## Headline results (numbers from the run)
| filter (in feedback path) | att@21.4 | ph@3Hz (feel) | |1−L|min | worstRe | hard edge | poles r |
|---|---|---|---|---|---|---|
| **BARE loop (V38 4×)** | 0 dB | 0° | **0.139** (~1.2 dB) | 0.86 @20.2Hz | 4.66× | — |
| **V48B notch Q5 −8 dB** | −7.9 dB | −1.5° | **0.400** | 0.60 @17.9Hz | 6.67× | 0.979 |
| **notch Q2 −8 dB** | −8.0 dB | −3.9° | **0.581** | 0.42 @17.5Hz | 9.61× | 0.948 |
| notch Q1.5 −10 dB | −10 dB | −6.5° | 0.675 | 0.32 | 12.4× | 0.923 |
| 1st-order LP fc=10 Hz | −7.5 dB | −16.2° | 0.697 | 0.27 | 14.6× | (real pole) |
| 2nd-order LP fc=12 Hz | −12.4 dB | −27.0° | 0.831 | 0.16 | 25.2× | (real poles) |

Stable under ±30° carrier-phase model error for both front-runners (Q2 notch and 10 Hz LP).

## What this means (the reframe)
1. **The notch CONCEPT is Gate-2 sound.** As a pure filter the V48B notch does not destabilize the
   base-assist loop in the calibrated model — it *improves* the closest approach to +1 from 0.139 to
   0.400 and pushes the hard self-excitation edge from 4.66× out to 6.67×. Its own resonator poles
   (r=0.979) do NOT open a new dangerous real-axis crossing (worst moves to 17.9 Hz at Re=0.60 < 1).
2. **=> the violent V48B brick was the RAM COLLISION (Gate 1), not closed-loop instability.** Fixing
   the RAM is the load-bearing repair. This does NOT retract Gate 2 — Gate 2 was genuinely unanalyzed,
   and analyzing it is what let us conclude this.
3. **V48B's Q5 notch is a needlessly lightly-damped resonator.** A **Q2 −8 dB** notch is strictly
   better on every stability axis (poles r=0.948 vs 0.979, worstRe 0.42 vs 0.60, edge 9.6× vs 6.7×) at
   the SAME −8 dB depth and negligible feel cost (−0.05 dB / −3.9° at 3 Hz). It is the direct,
   principled answer to the "lightly-damped resonator" Gate-2 objection: make the resonator well-damped.
4. A first-order low-pass is even more robust but costs real base-assist feel (−16° phase lag at 3 Hz)
   — not preferred given the notch preserves feel (unity DC) while now also passing Gate 2.

## Caveats (calibration discipline)
- This is a MODEL: ONE resonance, a rate-dominant carrier, a 1.5-sample delay. It reproduces the anchor
  exactly and the verdict survives ±30° carrier-lag error, but it cannot see a *second* mechanical mode
  or fine discrete-time effects. The Q2 damping choice (wider notch, gentler phase slope, smaller pole
  radius) is chosen partly to be robust to exactly that unmodeled risk.
- A code cave is still this kit's only bricking class (V24/V27/V48B). Gate 2 passing is necessary, not
  sufficient — first-minutes on-car observation remains the ultimate check, and Gate 1 (genuinely-free
  RAM, writers verified) must also be closed before any V48C is flash-ready.

## Related
[[reference-accord-v48b-flashed-catastrophic-ram-collision]] — the failure (RAM + never-analyzed loop).
[[feedback-cave-two-gates-ram-ownership-and-closed-loop]] — the two gates this closes (Gate 2 here).
[[reference-accord-v48b-notch-cave-build]] — the cave structure V48C reuses (new coeffs + new RAM).
