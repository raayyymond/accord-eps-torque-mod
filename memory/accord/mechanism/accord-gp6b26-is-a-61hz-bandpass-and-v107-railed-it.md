---
name: accord-gp6b26-is-a-61hz-bandpass-and-v107-railed-it
description: gp-0x6b26 is not a damper above ~30 Hz — it is a bandpass peaking at 61.1 Hz, and V107's dose made it rail into a Coulomb relay 33% of the time at 10-25 km/h.
metadata:
  node_type: memory
  type: reference
---

# `gp-0x6b26` IS A 61 Hz BANDPASS, AND V107 TURNED IT INTO A COULOMB RELAY

★★★★★ **EVIDENCE.** Two independent derivations of the transfer function, and a direct on-car
measurement of the consequence (route `1e`, V107, 988.6 s engaged, fault-free, 2026-08-26).

## THE LANE IS NOT A DIFFERENCER — IT IS A BANDPASS
```
H(f) = 64 · H1(f) · (1 − z⁻¹) · H2(f)
   H1, H2 = one-pole EMAs,  α0 = 37/128 = cal(0xC643C),  α2 = 22/64 = cal(0xC40DC),  fs = 1000 Hz

 f Hz     1     7.79   21.73    40    61.1    100    200    300    499
 |H|    0.40   3.08    7.72   11.15  12.14  10.86   7.15   5.45   4.49
```
**PEAK 61.1 Hz. −3 dB span 25.1 → 153.0 Hz. Never below 4.49× anywhere to Nyquist.**
At 100 Hz it runs at **10.86× — 40 % MORE gain than at the 21.7 Hz mode it was designed to damp.**
Derived independently from the image (`hfmech`) and from the kit's own 2026-08-10 trace (`arc-delta`);
the second reproduces that trace's recorded phase table to 2 dp at all six of its points.

## THE MEASUREMENT — IT RAILS
`|gp-0x6b26| = clamp( ((|c2c| · |Y_eff(v)|) >> 6) · 273 >> 18 , ±cal(0xC407E)=511 )` @`0x36CBE`..`0x36CCA`.
Reconstructed `P(|gp-0x6b26| = 511)`, engaged, episode-bootstrapped over 10 episodes:
```
   bin      V107 rail duty          V106, same samples
   <10      1.68% [0.86, 2.58]      1.47% EXACT
   10-25   32.32% [29.93, 35.68]    <= 15.46%
   24-40   21.27% [19.93, 22.51]    <= 10.45%
   40-64    4.27% [4.35, 6.31]      <=  3.43%
   >=65    <= 0.23% / <= 0.03%      same
```
**Duty is EXACT where the clamp threshold sits at or below the 1636.8-count wire rail, and two-sided
bounded above it.** V107's own builder predicted **≤1.05 % everywhere** and rejected its alternative at
6.2 % as *"V80 relay territory"*. A railed acceleration term is `sign(α)·511` — a bang-bang **Coulomb
relay**, precisely `accord-v80-damper-relay-and-grind1-inert`'s mechanism.

## WHY THE SAFETY CASE COULD NOT SEE IT
**CAN 427 (`0x1AB`) arrives at 49.8 Hz — Nyquist 24.9 Hz. The lane's entire −3 dB band is above that.**
The instrument was structurally blind to the passband of the thing it was sizing.
🛑 **And the prediction METHOD is void, not just under-ranged.** `|b26|_X(v) = |b26|_meas(v) × Y_X/Y_route`
is an open-loop push-through that assumes the `gp-0x6c2c` distribution is invariant to `K`. But
`gp-0x6b26` → aggregator → motor → motor rate → `gp-0x6c2c`: **it is a closed loop.** Predicted ≤1.05 %,
measured 33.49 % — a **32× miss**, reached independently from the code and from the data.
⇒ **No open-loop duty prediction on this lane can be trusted again.**

## THE SUPPORTING SIGNATURES
- **Sub-perceptible input is enough.** At V107's 24 km/h dose the peak column displacement that fully
  rails the clamp is **1.88° at 7.79 Hz, 0.27° at 21.7 Hz, and 0.042° (2.5 arcminutes) at 100 Hz.**
- **The 2×2:** holding Y fixed, **engaged `|c2c|` alone gives 27× the rail duty of manual `|c2c|`** at
  10–25 km/h. The dominant term is not the mode record — engaging makes the motor acceleration itself
  far larger, and Y amplifies what is already there. A feedback signature.
- **The symptom map and the rail-duty map are the same map.** V107 shrank the rail threshold **1.42–2.71×**
  across 24–90 km/h and left Y[0] byte-identical below 20 km/h; the operator reports grinding at
  15–40 mph and none below 5–6 mph.
- 🛑 **`H(0) = 0` DOES NOT SAVE IT.** That proof is a property of the LINEAR lane. A railed term is a
  **constant 511-count DC drag = 10.7 % of the 4762 governor ceiling** through the whole acceleration
  phase. *"Cannot bias a HELD command"* stands; ***"cannot cap achieved PEAK rate" is VOID once railing
  is in play.*** Consistent with `|d(rate)/dt|` p90 collapsing 2529 → 657 at 40–70 km/h for a nominal
  2× dose step.
- **A phase sector crossing at 74.5 Hz.** The standing *"gp-0x6b26 can never RAISE a resonance"* result
  was only ever verified **to 40 Hz**; above 74.5 Hz the phasor sits in 90–180° continuously to Nyquist.
  [BELIEF — structurally supported, not proven.]

## THE FIX SHAPE
Lowering Y de-rails but pays one-for-one at 21.7 Hz (Y is a flat multiplier). **`cal(0xC40DC)` (α2) at
14/64 holds 21.73 Hz EXACTLY while cutting 20–35 % over 61–300 Hz** — see
[[accord-c40dc-is-the-band-limit-lever]].

Related: [[accord-v80-damper-relay-and-grind1-inert]] · [[accord-gp6b26-is-inertia-not-damping]] ·
[[accord-v106-gp6b26-mechanism-ceiling-and-reshape]] · [[accord-the-8x-gain-is-the-carrier]]
