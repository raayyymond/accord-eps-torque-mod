---
name: accord-the-rate-deficit-is-real-universal-and-not-v111
description: "MEASURED against openpilot's true demand channel: the car achieves only 0.73/0.63/0.47/0.30 of demanded steering rate at 5-15/15-30/30-60/60+ deg/s, and openpilot is command-RAILED at STEER_MAX 17/32/50 percent of the time in the top three bands. The deficit is present on ALL 18 cached routes, so V111 did NOT cause it and reverting alpha2 will NOT fix it. Four candidate firmware clamps are EXCLUDED by arithmetic."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑★★★★★ THE STEERING-RATE DEFICIT IS **REAL, LARGE, AND UNIVERSAL** — AND V111 DID NOT CAUSE IT

Measured 2026-08-27 across **18 cached routes**, answering the operator's standing question
(*"it feels like the max angular velocity has not scaled 6x"*). **He is right.**

## THE MEASUREMENT [EVIDENCE]
Demand = `d/dt` of `controlsState.desiredCurvature` mapped to column angle by the route's own
`ang = a*curv + b` fit; achieved = CAN `STEER_ANGLE_RATE`. Engaged & hands-off (D3) & moving.

```
  CORPUS POOLED (18 routes, weighted by n)
  demanded deg/s     n        RAIL DUTY (|cmd| >= 4090)     achieved/demanded
      5 - 15      103158            5.9 %                        0.73
     15 - 30       36595           16.9 %                        0.63
     30 - 60       18137           32.0 %                        0.47
     60 +          13407           49.8 %                        0.30
```
🛑 **Rail duty rises monotonically with demand.** At high demand openpilot is emitting its absolute
maximum (`STEER_MAX = 4096`) **half the time** and still gets **30 %** of the motion it asks for.
⇒ **The LKAS path is AUTHORITY-STARVED, not merely mis-tuned.**

⊕ **Not a plant limit.** On the same car, same speeds, the **driver reaches 335.2 °/s**
(5–15 mph manual, p99 316.7) while **LKAS at a railed 4096 command reaches 84.6 °/s** — a 4x gap.
⊕ **Not a hard clip.** The 84.6 °/s engaged maximum has **no pile-up**: 2 samples within 5 % of it
(0.003 %) vs 13 (0.21 %) for manual, and the engaged max varies with speed (41.5 -> 84.6 -> 37.0).
It is a **soft roll-off**, not a wall.

## ⭐⭐ IT IS NOT A V111 REGRESSION — WHICH RETIRES THE α2 REVERT
`ach/dem` in the 60+ band, every route: **0.09 – 0.49, corpus median ~0.26.**
**Route 21 (V111) = 0.24 — dead typical.** The deficit is present on *every* build in the corpus.
🛑 ⇒ **Reverting `0xC40DC` α2 14->22 will NOT restore the steering rate**, and the mechanism proposed
in [[accord-v111-flew-alpha2-is-the-only-delta]] (*"EMA lag rotates inertia into friction ⇒ that is
what caps velocity"*) **cannot be the cause of a deficit that predates it.** Downgrade that story to
"may explain the *change in feel*"; it does **not** explain the rate ceiling.
⊕ `gp-0x6b26` is bounded by `cal(0xC407E) = 511` — **confirmed by decompile of `FUN_00036c12`**, where
the clamp operand is `tp+0x507E`. Against a ±20 000 residual that is **<= 2.6 % of range**, and the α2
change moves only its *friction component* (`d(|H|*sin phi)` ~ 0.078 at 8 Hz) ⇒ **<= ~40 counts, 0.2 %
of range.** Far too small to explain a felt loss of rate. [EVIDENCE, arithmetic.]

## 🛑 FOUR CANDIDATE CLAMPS **EXCLUDED** — do not re-propose them
| candidate | why it is dead |
|---|---|
| `0xC520C` motor-rate cap table | **already struck**; measured dead on route `a6` (peak 1462 ct, 0.11 % above X[0]) |
| `0xC6202` governor = **4762** | LKAS at full command = `15360*5346>>15` = **2506** < 4762; hands-off the assist addend is small. ⚠ Also lockstep-shadowed -> fault `0x17` |
| `0xC61B2`/`0xC61B4` arb clamp = **3072** | full-command arb output **2506 < 3072** ⇒ never bites at 6x (it would at >=7.35x) |
| a hard rate clip at 84.6 °/s | **no pile-up** (see above) |
⊕ `0xC646C` is still **891 on every build**; the 6x lives on `0xC6CD0` = **5346** (5346/891 = **6.000x**).

## ⭐ WHAT THIS MEANS FOR THE NEXT BUILD
`STEER_MAX` is openpilot-side and off-limits ([[feedback-no-openpilot-side-modifications]]), so the
useful firmware lever is **anything that delivers more wheel motion per unit of command, without
adding impedance** — exactly [[feedback-do-not-buy-ratchet-with-mass-and-friction]].
⭐ **This independently confirms the V112 relay lever from a different direction.** V112 pushes the
Coulomb corner 10.6 -> 31.8 °/s, so its friction *compensation* keeps climbing instead of clipping
across **10.6–31.8 °/s — precisely the band where `ach/dem` falls 0.63 -> 0.47** — and more friction
compensation means **more assist** ([[accord-friction-polarity-more-assist]]).
See [[accord-knee-and-k1-decouple-lightness-from-relayness]].

## 🛑 TWO RETRACTIONS FROM THIS SESSION — both caught by their own controls
1. ~~"rate compresses against command (1024->4096 buys 1.39x where linear predicts 2.7x)"~~ —
   **matched on speed and angle but NOT on demand.** High command also means *holding* a turn.
   Conditioning on demand dissolves it.
2. ~~"the car delivers 89–107 % of demand ⇒ rate is not firmware-limited"~~ — **used `ct_curv`
   (`controlsState.curvature` = CURRENT) as the demand. Circular.** The tell was `r = -0.9995`
   against measured angle. The true demand channels are **`ct_dcurv`** (`desiredCurvature`) and
   **`cc_curv`** (`actuators.curvature`), which agree to 3 dp and give 0.92 -> 0.30.
🛑 **LESSON: in this cache, `ct_curv`/`cc_ccurv` are CURRENT; `ct_dcurv`/`cc_curv` are DEMAND.**
Any "tracking" result built on the first pair is circular by construction.

## ⚠ WHAT IS **NOT** ESTABLISHED
- **Where** the roll-off comes from. Four clamps are excluded; the remaining candidates are the
  loop bandwidth itself, the LKAS lane low-pass, and plant load. **Unresolved.**
- The 60+ °/s demand band is partly **planner steps** (a step in `desiredCurvature` differentiates to
  a spike no steering system could follow). The **15–30 °/s band (`ach/dem` 0.63, rail duty 16.9 %)
  carries the argument** — it is ordinary, sustained and physically reachable.
