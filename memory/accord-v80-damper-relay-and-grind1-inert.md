---
name: accord-v80-damper-relay-and-grind1-inert
description: "V80 flew route 66 with the worst grinding ever — the damper became a Coulomb relay; and grind #1 is INERT to the damper dose, retracting the \"optimum in k\" framing."
metadata: 
  node_type: memory
  type: reference
  originSessionId: a1847153-0209-46d3-8a3d-e363459b6352
  modified: 2026-08-07T19:41:21.411Z
---

**V80 FLASHED AND FLOWN**, route `75604b0a432fdc89|00000066--276b942769` (15 segs, 901.7 s, engaged
33.62%). Operator: **the worst grinding the car has ever produced** — loud, whole-car, ~90% of engaged
time, both low and high speed, causing instability. 🛑 **It did NOT fault** — 0 DTC transitions. A
*stability* failure, not a fault-class one.

## ROOT CAUSE [EVIDENCE — orchestrator's own LE read of the flashed images + numeric describing function]
V80's damper is a **near-bang-bang Coulomb relay**: above ~119 counts (~25 °/s) of motor rate it emits a
**constant ~495 counts — 3.4% variation across a 34× rate range — at 97% of its 512 ceiling, at EVERY
speed** (FactorC flattened to 566). V75 plateaus at **297 (58% of ceiling)** and only above 54 °/s.
Relay-ness index `N(50)/N(500)`: **V75 1.45× · V80 3.27×**. Loop gain `k`: V74 0.58 · V76 1.39 ·
**V75 1.58 · V80 4.16**.

🛑 **The no-clip gate was structurally blind.** Every guard tests `product > ceiling`; V80's supremum is
`(566*927)>>10 = 512` = the ceiling **exactly**, so it clips 0.00% and passes. **"Does not clip" and
"is not a relay" are different statements.** The relay was moved from the ceiling clamp to FactorE's own
knee, 17 counts under the rail. Put this in every future gate.

## THE MEASUREMENT THAT SETTLES IT — both builds' own cave probes
`|gp-0x6bd0| ≥ 448 counts`, engaged: **V75 0.000%** (28,317 frames; never above 128 counts at all above
40 km/h) vs **V80 19.4%**, 32.7% above 15 m/s, **71% through the worst 29 s event.**
V75's damper never entered its saturated regime. V80's lives there.

## WHAT V80 ACTUALLY PRODUCED
- A **2.09× [1.46, 2.70] broadband lift of everything above ~24 Hz** — flat, prominence-neutral; a
  pre-declared 32–38 Hz negative control fails identically (2.035) ⇒ not "grind #2 got worse".
  **IMU vertical 1.07 [0.92, 1.33] ⇒ NOT a rougher road.** FFT-free confirmation: engaged windows with a
  sample-to-sample reversal >300 counts — **V75 3.0% · V74 22% · V76 22% · V80 73%**.
- A **sustained 27.4 Hz, Q ≈ 140 limit cycle** (worst event: seg 8, route t ≈ 501–530 s, 100 km/h, 30 s
  unbroken, bar 6,830 ct p-p, wheel ±1°). Windows >1000 ct in 26–31 Hz: **V74 0/413 · V76 0/328 ·
  V75 0/133 · V80 32/215.** Speed-INVARIANT frequency (`df/dv` = −0.131 [−0.231, −0.016] Hz per m/s;
  wheel order 2 demands +0.961) with amplitude exploding with speed (×2.1 at 1–5 m/s → ×94.9 at 24–32).
  ⚠ Not new to V80 — the kit's ~28 Hz line, amplified ~2.7× and made self-sustaining.

## 🛑 RETRACTION — GRIND #1 IS INERT TO THE DAMPER DOSE
Four-point ladder on one instrument, ratio to V76, episode-block bootstrap:
18–22 Hz — V74 1.166 [0.98,1.41] · V76 1.000 · V75 0.735 [0.50,1.22] · V80 0.835 [0.64,1.07].
**Split-half null ≈ [0.63, 1.60]. Every point is inside it, across k = 0.58 → 4.16.**
⇒ **V80 did not overshoot an optimum — grind #1 never responded to k.** V75's "no grind #1" vs V76's
"still grind #1" is a **creep-EXPOSURE difference** (V76's creep windows carry 3.4× V75's effort).
⇒ Any claim of a dose-response on grind #1 must be re-checked against this. ⚠ Also retracted: "V80 is
quieter than V76 at creep" — V80's creep windows have 25× less wheel motion; **zero matched cells.**

★ The usable statement: **k ∈ [1.39, 1.58] buys most of the ratchet benefit at zero HF cost; something
switches on between 1.58 and 4.16 that costs 2× broadband HF plus a limit cycle. Where in that gap is
UNMEASURED.** The micro-ratchet improves **monotonically** with k and is best at V80's dose (0.418
[0.33, 0.61]) — V80 bought a real ratchet gain and paid for it with the HF floor.
⇒ The data's own prescription: **restore the RAMP, don't merely lower k.**

Related: [[accord-c407e-is-the-fault-interlock-c63a0-exonerated]] · [[accord-v81-built-v75-minus-fault-cells]] ·
[[reference-accord-car-is-tvca4-mode-24-26]] · [[feedback-episodes-not-windows]] ·
[[accord-averaged-spectrum-needs-matched-speed-distributions]] · [[accord-v62-fixed-the-grinding]]
