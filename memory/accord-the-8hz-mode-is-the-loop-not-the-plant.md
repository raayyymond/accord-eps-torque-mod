---
name: accord-the-8hz-mode-is-the-loop-not-the-plant
description: The loop is IDENTIFIED — |kG| = 0.63, gain margin 1.2-1.6x, and the passive plant is a near-lossless spring, so 100% of the measured Re(Z) = -3761 at 6-9 Hz is LOOP-GENERATED, not a mechanical resonance being excited.
metadata:
  type: reference
---

🛑🛑 **THE 8 Hz RATCHET MODE IS THE ASSIST LOOP'S OWN NEAR-INSTABILITY.** Identified 2026-08-21 from
the 4×/8× gain steps, both of which packed the aggregator **SUM** `gp-0x6b94` on the 427 lane
(routes `0x85` = V100 4×, `0x95` = V101 8×).

```
Z = Z0 / (1 + cG) ,  c = lambda*kappa ,  solved from  rho = Z_4x / Z_8x
|rho - 1| = 0.291 at 6-9 Hz  -> WELL-POSED  (15-22 and 21-22.5 Hz are NOT: 0.144 / 0.083)

c   = 13.09 @ +145.3 deg          |kG| = |P| = 0.630  [0.512, 1.001]
A   = 1 + P = 0.440 @ +25.0 deg   closed-loop amplification 1/|A| = 2.28x  [1.51, 9.4x]
Z0  = 2792 @ -92.45 deg           Re(Z0)/|Z0| = -0.043
```

⇒ **The identified PASSIVE plant is an almost perfectly lossless spring (~2296 counts/deg).**
⇒ **100 % of the measured `Re(Z) = -3761` at 6-9 Hz is LOOP-GENERATED.** Gain margin **1.2-1.6×**.

## THREE CHECKS THE SOLVE WAS FREE TO FAIL, AND DID NOT

1. **It recovered `kappa`'s sign from the firmware independently.** `arg(c) = +145.3°` against the
   structural prediction **+180°** (`kappa < 0`). The 34.7° gap is **exactly 12.8 ms of actuation lag
   at 7.5 Hz** — the right size for shaper + integrator + FOC. The solve knew nothing about it.
2. **The identified plant came back physical** — a near-lossless spring, which is what a torsion bar
   *should* be.
3. **Within-drive replication, no cross-build assumption.** Stratifying route `0x85`'s own windows by
   `p75(|tq|)`, the well-posed 700-1200 × >2000 ct pair returns `c = 13.82 @ +141.3°`, `|P| = 0.634`,
   `|1+P| = 0.418` — matching the cross-build answer. Ill-posed pairs return garbage, as they must.
   Every leave-one-out keeps `|A| < 1`.

## WHY EVERY FILTER LEVER FAILED — the one-line reason

**A resonant pole contributes −90° at its own pole frequency, which is the wrong sign.** Both
directions of Honda's biquad were killed on this: the **notch** (`Re(u/T)` rises monotonically across
6.0-9.5 Hz, ratio 2.08-2.37×, `ΔRe(Z)` = −461…−3028 ⇒ MORE anti-damping) and the **boost** (a 2-pole
section's −77.8° makes `|ΔH| = 1.378` larger than `|H|` itself ⇒ `|u|` → **3.34×**, plus a Nyquist
encirclement at every `r`).
⇒ **The matched fix is a DIFFERENTIATOR (+90°): active damping `−K·phi'`.**

## SIZING — quantitative for the first time in the kit's history

`ΔP = c·ΔG`, `|c| = 13.09`. **`ΔG = 0.047`** (89 % of the whole sum `|G| = 0.048`) takes
**`|A|` 0.44 → 0.87**. A **lane-sized dose is ~4× over.** A **wrong sign** at that magnitude drives
`|A|` to ~0.15 — a **6.7× amplification.** 🛑 **Pre-register the sign readout on any dose.**

## 🛑 THE LAW THIS PRODUCED

> **At 6-9 Hz the aggregator is a 4:1 near-CANCELLATION — individual lanes are LARGER than their sum
> (`coh2(T, sum)` = 0.279 vs `coh2(T, lane)` = 0.80-0.89). ANY single-lane perturbation is amplified
> ~4× at the output. SIZE EVERY 6-9 Hz LEVER AGAINST THE SUM (0.053), NEVER AGAINST A LANE.**

The cancellation is **band-specific**: at 21.0-22.5 Hz the ratio is only 1.68, and at 2.5-4.5 and
15-22 Hz sum and lane are comparable. This retroactively explains why sixty builds of lane-sized doses
produced nothing, or produced the opposite of what was predicted.

## CONSEQUENCE FOR GAIN

**The LKAS gain ceiling is a STABILITY problem, not a clamp problem, and it was already hit at 8×.**
V101 had 13.0 % arb-clamp margin and +25.2 % governor margin — inside every limit — and produced the
operator's worst vibration report, with the **resonance peak MOVING 20.3 → 23.0 Hz** (a root-locus
signature; excitation does not move a peak). `|kG|` 0.63 @4× → 0.75 @8×, extrapolating to **0.97-2.0
at 16×**. ⇒ **Damping is the PREREQUISITE for more gain, not a detour.** Scaling is sub-linear
(1.19× of `|kG|` for a 2× gain step), so margin bought at 8 Hz converts into more gain than linear
intuition suggests.

## LARGEST REMAINING WEAKNESS

**Route `0x85` contributed only 2 engaged episodes and `0x95` three.** Dropping one of r85's swings
`|A|` 0.44 → 0.18. **Repoint the 427 lane back to `gp-0x6b94` (a proven 2-byte edit, `0x55DF2`, flown
at V100) and fly it** — ≥6 episodes of ≥10 s, with ≥12 windows at `p75(|tq|) > 2000 ct`. That makes
the model **over-determined** (4×/6×/8× all on the sum) and therefore falsifiable rather than merely
fitted.

Related: [[accord-rez-antidamping-replicated-three-drives]] · [[accord-the-8x-gain-is-the-carrier]] ·
[[accord-ratchet-is-a-lightly-damped-resonance]] · [[accord-f0-crossover-is-the-endpoint]] ·
[[accord-r24r26-live-gain-is-default-lerp]] · [[accord-ldbu-displacement-lowbit-in-hw1]]
