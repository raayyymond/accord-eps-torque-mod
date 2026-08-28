# V118 — PRE-REGISTERED SCORING, written before the drive exists

`image 8a0f0080…` · `.rwd 92b798a1…` · builder `analysis-2020accord/builds/v108_plus/build_v118_tva.py` (43/43)
Base V112. Edits: `0xC649B` 1→0 · `0x55DF2` `gp-0x6ABC`→`gp-0x67FA` · `0x55E10` sar 3→0.

🛑 **Everything below is fixed NOW.** The point of pre-registering is that a null result stays a null
result — this kit has repeatedly produced findings that died to controls run afterwards.

## 0. IDENTITY — prove V118 is the build on the car, before anything else
The 427 wire changes meaning, and that is itself the identity signature:
- **V112 and earlier:** wire = `min(|gp-0x6abc|·5 >> 3, 1023)` — a broad rate distribution,
  p50 ≈ 4, p99 ≈ 500, max ≈ 935 (measured on routes 22/23).
- **V118:** wire = `min(|gp-0x67fa|·5, 1023)` — a **DISCRETE** set `{0, 5, 10, …, 75}`.
🛑 **If the wire is not discrete-and-small, V118 is NOT on the car. Stop and say so.**
⊕ Any value **≥ 1023** = high-byte contamination from `gp-0x67fb`; **discard those samples**, do not
misread them. Report the contaminated fraction.

## 1. STATE-4 DUTY — the decisive diagnostic (`0x454FE`)
`state = wire / 5`. **STATE 4 ⇒ WIRE 20.**
Report `P(state == 4)` **overall**, **engaged**, and **by speed bin** (0–15, 15–35, 35–55, 55–80 km/h).
| outcome | what it licenses |
|---|---|
| **duty ≥ 5 % engaged** | `0x454FE`'s deletion is live and becomes the prime suspect. The fix is a **modified restore** of `FUN_00049A5A`, **never a blind revert** (V42's change is a validated fix for the V38 macro ratchet). |
| **1 % ≤ duty < 5 %** | live but marginal — size its contribution before proposing anything. |
| **duty < 1 % engaged** | 🛑 **`0x454FE` is ELIMINATED.** The search moves to the V57 gain repoint, the LKAS ceiling raise ×1.067, and the ~20 remaining cal cells. |

## 2. THE BIQUAD EFFECT — the candidate fix (`0xC649B`)
**Primary statistic:** `Re(Z) = Re(H1[cs_rate → cs_tq])` averaged over **7–9 Hz**, mask
`engaged ∧ rolling-median|cs_tq| < 1200 ∧ v > 1 m/s`, Welch 2048-pt @100 Hz.
**Comparison:** V112's own routes 22 + 23 pooled. **Their measured values are −50.1 and −74.8.**
**Null:** a **within-V118 split-half** on the new route — split its engaged blocks into two halves and
take the difference. **Quote the null BEFORE the contrast.**
| outcome | verdict |
|---|---|
| V118 less anti-damped than V112 by **more than the split-half null half-width** | the biquad is a real contributor ⇒ next step is **reshaping** its coefficients, not merely disarming |
| difference **inside** the null | 🛑 **biquad ELIMINATED** — as the corpus already hinted (P = 0.722, not separable) |
| V118 **more** anti-damped | arming it was doing useful work ⇒ **revert the one byte** |
⚠ **Route-to-route spread on this statistic is −31.9 … −74.8 across the corpus — larger than the
effect being sought.** A single route cannot settle it on its own; **the split-half null is what
makes the comparison honest**, and if the null is wide the answer is NOT RESOLVED, not "no effect".

## 3. THE OPERATOR'S OWN READ — the primary outcome, as always
Score the **symptoms**, not the bands: is the fixed oscillation at the peak of a hard curve weaker,
unchanged, or worse? Is grind #1 changed? **V118 is not expected to touch grind #1** — that band
(18–22 Hz) measures `Re(Z)` −1 to −10, essentially neutral, so it is a different mechanism.

## 4. WHAT THIS DRIVE CANNOT DO
It cannot separate the **V57 gain repoint** from "being a modified build at all" — every modified
route carries it and stock is the only 1× point. That needs a different experiment entirely.
