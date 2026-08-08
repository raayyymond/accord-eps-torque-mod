---
name: reference_accord_v81_engagement_impedance_factorce_dominant_mechanism
description: V81's FactorC/E damper dose is the only mechanism that makes manual steering feel heavier and LKAS angle rate slower specifically when LKAS is engaged.
metadata:
  type: reference
---

[EVIDENCE, byte-level] Answers the operator's V81 report: "manual steering, even same-direction as LKAS,
feels MUCH HARDER than with LKAS disengaged" + "LKAS steering angle rate is very limited". Builds on
[[reference_accord_mode24_mode26_stock_boost_friction_gainb_identical]] (the negative census that rules
almost everything else out).

## The mechanism
V81 = V75's damper dose, with only `0xC407E` and friction reverted to stock
([[accord-v81-built-v75-minus-fault-cells]]). Its mode-26-only (engaged) FactorC/E records:
- FactorC (`0xC9E9C[26]` → `0xD77D0`): `Y[0]` raised 0 → **566**, applying at ANY speed ≤ 35 km/h
  (X[0]=2240 unchanged) — mode 24 stays byte-stock (Y[0]=0).
- FactorE (`0xC9F84[26]` → `0xD780C`): `X=[12,200,2500,4000] Y=[0,539,539,927]` — dead-zone knee dropped
  from 60 → 12 counts (≈2.5 °/s) and the ramp compressed into [12,200]. Mode 24 stays byte-stock
  (X0=60, ramp to 400).
- k = (566·539)>>10 / (200−12) = 1.579, matching the recorded "V81 == V75's k=1.5798 exactly" — a
  self-consistency check that PASSED.

Damper product `(FactorC·FactorE)>>10`, ceiling 512, at representative motor rates:

| rate (ct / °/s) | 20 / 4 | 99 / 21 | 200 / 42 | 500 / 106 |
|---|---|---|---|---|
| mode 24 (manual, V81==stock) | 0 | 0 | 0 | 0 |
| mode 26 (engaged, V81) | 82 (16%) | 138 (27%) | 297 (58%) | 297 (58%) |

The damper is dissipative by construction (`sign(gp-0x6bd0) = -sign(motor rate)`, see
[[reference_accord_damper_net_sign_resolved_and_gp6b94_forward_gap_narrowed]]) and reacts to raw motor
rate magnitude — **it does not know or care whether the rate was commanded by LKAS or produced by the
driver's own hands.** ⇒ engaging LKAS alone (regardless of what LKAS then commands) turns on 16-58% of
full damper authority against ANY steering motion, manual or commanded, that did not exist in manual
mode at all (mode 24 damper == 0 at these rates, by the stock dead-zone). This single mechanism explains
both halves of the report: heavier manual effort under engagement, and suppressed realized LKAS angle
rate (the damper fights the LKAS's own commanded rate too).

🛑 Open, not resolved this session: the exact `gp-0x6b94 → motor PWM` instruction hop is still
unclosed (long-standing gap, see [[reference_accord_damper_net_sign_resolved_and_gp6b94_forward_gap_narrowed]]).
The SIGN and the aggregator arrival are proven; the very last hop is [BELIEF] structurally but
[EVIDENCE] empirically — V74/V75/V80's own dose-response experiments already showed on-car spectral/
feel changes tracking k, so the damper demonstrably reaches the driver somehow.

## Candidate cal-only test — UNTESTED, not falsified
Revert V81's mode-26 FactorC/E records to literal stock bytes (`0xD77D0` Y=[0,234,429,908];
`0xD780C` X=[60,400,2500,4000] Y=[0,140,539,927]) while keeping `0xC407E=511` and friction=stock as-is.
Grepped `build_v72..v81_tva.py` — **this exact combination (fault fix + full FactorC/E revert on mode 26
only) has never been built.** Cost: gives back whatever ratchet suppression the k=1.58 dose bought
(V80's own dose-response table: k∈[1.39,1.58] "buys most of the ratchet benefit" per
[[accord-v80-damper-relay-and-grind1-inert]]).

## Ranked candidates for the operator's report (full detail in the session's SendMessage to team-lead)
1. FactorC/E engaged-only dose — dominant, only asymmetric mechanism found anywhere.
2. `0xC63A0`=2048 (Path-2 weight, 2× stock, kept deliberately in V81) — real but mode-proof/symmetric,
   a general loop-gain lever not an engagement-specific one.
3. [BELIEF] `FUN_0003a382`'s P/I/D gain LERPs share `gp-0x6ac0` (rate) as their index with FactorE, so
   they compound with #1 once engaged, but aren't mode-gated on their own.

## T5 (frame challenge): the goal conflict is structural to the CURRENT wiring, not to the physics
FactorE is a bare rate-magnitude damper (no frequency selectivity) — it can't distinguish the 6-9 Hz
ratchet or 18-22 Hz grind from the LKAS's own desired steering rate or the driver's slow hand input,
which is mechanically why suppressing bad frequencies and preserving angle rate fight on this lever.
FactorD (the one non-rate axis, angle-tracking error) is confirmed flat/inert (Y=1024) in BOTH modes —
Honda never populated it, so it isn't a free escape hatch. A genuine frequency-selective fix would need
a real notch on the same rate signal — a CODE cave, this kit's only bricking class (V24/V27/V48B) — not
cal-only. I did not re-run a fresh notch/biquad search this session; relying on the standing negative
result (deliberately marking that inheritance [BELIEF], not re-confirmed [EVIDENCE]).
