---
name: accord-the-damping-route-is-closed-by-the-rail
description: "The engaged damper cannot be increased where the oscillation lives. Y[0] has only 1.11x int16 headroom, and Y[1] - the knot that governs 20 km/h and dominates the 35 km/h interpolation where the oscillation sits - was already flown at -24000 on V107 and MEASURED to rail 32.32 percent of the time at 10-25 km/h and 21.27 percent at 24-40. V108 reverted it for that reason. So the binding constraint is not int16 but the +-511 clamp at 0xC407E, and that cell cannot be raised because V73 raised it and V74/V75 hard-faulted. The damping route is closed on measurement, which leaves excitation reduction as the only remaining direction."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑 THE DAMPING ROUTE IS **CLOSED** — by the rail, not by int16

## THE BUILD I WAS ABOUT TO PROPOSE
The engaged friction row is the one lever whose direction is **measured on the road**
([[accord-the-added-lkas-mass-is-the-damper-that-works]] — V94 cut it 6× and the operator aborted;
delivered phase +137° vs wheel rate). `Y[0]` has only **1.11×** int16 headroom, **but `Y[1]` has
1.90× and `Y[2]` 2.05×** — and the oscillation's median speed, **35 km/h**, sits between the
`X[1] = 20` and `X[2] = 90` km/h knots. ⇒ *"raise Y[1] and Y[2], add damping exactly where the
symptom is, leave Y[0] alone so creep clamp duty is unchanged by construction."*
⊕ And `Y[1] = -24000` is **flight-proven** — V107 flew it.

## 🛑 IT IS ALREADY MEASURED HARMFUL, AND THAT IS WHY V108 REVERTED IT
`build_v108_tva.py` E2, measured on route `1e`, **episode-bootstrapped over 10 episodes**:
```
   bin (km/h)   V107 rail duty  (Y1 = -24000)     V106/V108  (Y1 = -17202)
     <10         1.68 % [0.86, 2.58]               1.47 % EXACT
    10-25       32.32 % [29.93, 35.68]            <= 15.46 %
    24-40       21.27 % [19.93, 22.51]            <= 10.45 %
    40-64        4.27 % [4.35, 6.31]              <=  3.43 %
    65-90       <= 0.23 %                         <=  0.23 %
      90+       <= 0.03 %                         <=  0.03 %
```
🛑 **At `Y[1] = -24000` the term hits its ±511 clamp 32 % of the time at 10-25 km/h.** A damper
that rails a third of the time **is a relay** — the exact class that made V80 *"the worst grinding
ever recorded"* ([[accord-v80-damper-relay-and-grind1-inert]]). ⇒ **restoring Y[1] would rebuild
that.**
⚠ And at **24-40 km/h — where the oscillation actually lives — V108 ALREADY rails ≤ 10.45 %.**
⇒ **There is no safe headroom to add damping at the symptom's own speed.**

## ✅ THE BINDING CONSTRAINT IS THE ±511 RAIL, AND IT IS HARD-BLOCKED
The limit is **not** int16; it is `gp-0x6b26`'s clamp at `cal(0xC407E) = 511`.
🛑 **That cell cannot be raised:** Honda ships it at 511, one count under its own 512 trip, and
**V73 raised it ⇒ V74/V75 HARD-FAULTED** ([[accord-c407e-is-the-fault-interlock-c63a0-exonerated]]).
⇒ more damping at 20-40 km/h requires more rail, more rail requires raising `0xC407E`, and raising
`0xC407E` faults the ECU. **The route is closed.**

## ⇒ WHAT THIS LEAVES
✅ **Only EXCITATION reduction remains.** Adding dissipation is exhausted where the symptom lives;
the remaining move is to put less energy into the resonance. **That is exactly what V121 does**
(relay knee 1800→3000, softening the signum that
[[accord-the-7to9hz-mode-is-nonlinearly-excited-harmonics]] indicts as the excitation path).
⇒ **V121's case is strengthened BY ELIMINATION**, not by new evidence for its mechanism — its
harmonic rationale is still [BELIEF] and its effect is still UNKNOWN. But it is now the **only
remaining direction** on this symptom that is not measured-closed.
⊕ `Y[2]` alone (≥90 km/h, rail duty ≤ 0.03 %) does have headroom, but raising it moves the
35 km/h delivered coefficient only **1.10×** — not worth a flight on its own.
