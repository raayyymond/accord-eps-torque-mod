---
name: accord-base-assist-damper-cannot-reach-the-micro-regime
description: FactorC x FactorE is a product of two dead zones; neither prior test ever had both open, but sizing kills the lever anyway — reaching the micro regime needs a step at zero rate, the V80 move.
metadata:
  type: reference
---

**`ch₀ = clamp( (FactorC(speed) × FactorE(rate)) >> 10 , ±ceiling )`** — `gp-0x6bd0`, the
base-assist damper. Read from V88's own image, `analysis-2020accord/v89_b1_damper_surface.py`:

```
FactorC  ptr 0xC9E9C   X=[2240,3840,5120,8960] ct = [35, 60, 80, 140] km/h   Y=[0,234,429,908]
FactorE  ptr 0xC9F84   X=[  60, 400,2500,4000] ct = [12.7,84.9,530,849] °/s  Y=[0,140,539,927]
ceiling  ptr 0xC77A0   X=[300,800]  Y=[512,1024]
```
Mode 24 ≡ 26 and 25 ≡ 27, byte-identical (this car is TVCA4 — see
[[reference-accord-car-is-tvca4-mode-24-26]]).
🛑 **FactorE `X[0]` is 60 COUNTS, not 12.** "12.73 °/s" is X[0]'s *physical* value; "12" was the
proposed *edited* count in a withdrawn variant. Scale: **0.21217 °/s per count.**

## The measured consequence
On route 73's engaged frames the damper contributes **exactly zero on 95.91 %** of them —
including **100.0 %** of the operator's micro-ratcheting regime (229 s at |rate| 1–13 °/s) and
**100.0 %** of his ratcheting regime at parking-lot speed (131 s).

## ★ Neither prior test ever had BOTH dead zones open — a RULE-5 failure against a PRODUCT
- the **`FactorE X[0]` lever was withdrawn as "structurally vacuous"** — correct, but only *because
  FactorC was 0 at creep*;
- **`FactorC Y[0]` WAS tested, as V86B on route 70**, lifted to the record's own `Y[3]` (908/875) —
  but **FactorE stayed 0 below 12.7 °/s**, so V86B armed the damper only for *spinning quickly*,
  never for *spinning at all*. Operator on V86B: *"extra dampening on LKAS and in general at slow
  speed"* — the **cost was felt while the micro regime was never armed.**

## 🛑 But sizing closes it anyway — do NOT re-propose this lever
`ch₀` at creep (Q10, 1024 = full authority), with FactorC `Y[0]` lifted AND `FactorE X[0]` 60→12:

| |rate| °/s | 2 | 5 | 10 | 20 | 40 | 80 |
|---|---|---|---|---|---|---|---|
| V88 (Honda) | 0 | 0 | 0 | 0 | 0 | 0 |
| V86B (`Y[0]`=908) | 0 | 0 | 0 | 12 | 46 | 115 |
| + `X[0]`→12 | 0 | 3 | **10** | 25 | 55 | 116 |

Reaching even 25 % authority (256) at 10 °/s needs `FactorE(10 °/s) ≥ 288` — **unreachable by moving
X.** It requires raising **`Y[0]` off zero = a step at zero rate = a relay in rate**, which is the
V78/V79/V80 move recorded as **"WORST GRINDING EVER"** ([[accord-v80-damper-relay-and-grind1-inert]]).

⇒ **The base-assist damper cannot be the micro-ratcheting lever, cal-only.** Structural, not a null.
This kill saved a build that [[accord-ratchet-scales-with-wheel-rate]]'s grip result would otherwise
have strongly motivated.
