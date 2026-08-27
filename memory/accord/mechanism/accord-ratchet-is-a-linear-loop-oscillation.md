---
name: accord-ratchet-is-a-linear-loop-oscillation
description: "The ~7.79 Hz ratcheting is measured NOT a relay and NOT a plant resonance; it is a linear loop oscillation set by accumulated estimator lag, which makes PHASE/LAG a new lever class."
metadata:
  node_type: memory
  type: reference
---

★★★★★ **THE ~7.79 Hz RATCHETING IS A LINEAR LOOP OSCILLATION.** Measured 2026-08-09 on routes `6e`
and its predecessors. **This changes the CLASS of lever that can touch the one symptom the operator
says is unfixed.**

## IT IS NOT A RELAY [EVIDENCE]
| test | result | control |
|---|---|---|
| odd/even harmonic comb | **0.858 [0.739, 1.000]** | positive control **1.204 [1.147, 1.566]** at just **15%** injection |
| 3:1 phase-locking PLV | **z ≤ 1.05** | — |
| switching-surface time-locking | **−0.0375** | — |
| third harmonic, second method | **absent** | — |

⇒ **<15% of the ~8 Hz bar content can be relay-generated.** This **REFUTES** the friction-compensator
relay `FUN_00038148` / `gp-0x6b70` as the generator, and it disfavours `FUN_00036388`'s
relay-with-dwell for the same reason.

## IT IS NOT A PLANT RESONANCE [EVIDENCE]
The wheel-on-torsion-bar mode is **12.8 Hz [12.1, 13.6]** — **ABOVE** the ratchet — and **7.79 Hz is
unreachable through the plant alone** (12.65 Hz floor).

## ⇒ A LINEAR LOOP OSCILLATION SET BY ACCUMULATED ESTIMATOR LAG `[BELIEF]`
The only surviving hypothesis, and it fits **every** recorded property:
- sinusoidal, no comb ✅
- **speed-invariant**: slope **+0.074 / +0.049 / −0.004 Hz per m/s**, against wheel-order-2's predicted
  **+0.961** ✅
- engaged-only ✅ (the loop only closes engaged)
- present in the bar and in angle rate but **NOT in openpilot's command** ✅ (the loop closes inside the
  EPS + plant)

🛑 **THE IMPLIED LEVER CLASS — PHASE / LAG — IS NEW SINCE V38.** The whole arc moved magnitudes:
authority, gains, clamps, filter poles used as attenuators, damper surfaces, nonlinearity shape.
**Nothing has ever been aimed at *when* rather than *how much*.** V86 is the first.

## Two bounded supporting observations
- ⊕ **The line grew ~3× at V84 and V85 kept it** — speed-matched V85/V81 = **2.742**, V85/V84 = **0.850**.
  ⚠ *"V85's line is 3.2× more prominent"* is a **FLOOR EFFECT**, not an amplitude increase.
- ⊕ **NEW: a discrete engaged-only ~20.90 Hz line at creep on V85 and V84, absent on V81** (prominence
  **8.08×**), within noise of the recorded **21.09 Hz** engaged-only closed-loop mode. ⇒ **the 18–22 Hz
  V85-vs-V81 elevation is THAT LINE, not a floor shift.** ⚠ V84's arm is **n = 6 windows** — suggestive,
  not measured.
- ⊕ **Micro- vs macro-ratcheting could NOT be separated**: the split is dominated by speed, and kurtosis
  is consistent with **one population.** Do not treat them as two objects on this evidence.

## How to apply
Before proposing anything for ratcheting, ask **which dimension it moves**. A magnitude lever on a
linear loop mode changes amplitude at best and can raise loop gain at worst; **what moves a loop mode
is phase.** And check the frequency prediction, not the amplitude one — amplitude ratios have failed
four builds running against a **[0.63, 1.50]** split-half null.

Related: [[accord-ratchet-characterised-on-route-4f]], [[accord-v86-built-the-frequency-lever]],
[[accord-v85-flew-lever-delivered-bands-are-null]], [[accord-loop-does-not-close-through-openpilot]],
[[accord-firmware-adds-torque-to-bar-engaged-at-low-speed]].
