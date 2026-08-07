---
name: accord-factorc-dip-is-ours-and-factore-x0-is-not-a-noop
description: FactorC's X axis is vehicle speed at 64 counts/km-h; stock mode-26 Y is strictly monotone with NO dip — the dip is OURS (V74 -195, V75 -332). Monotone at C_Y0=566 is arithmetically impossible under the no-clip guard. FactorE X[0] 12->0 is NOT a no-op (196 of 4001 rate points change) but is far too small to be a fault fix.
metadata:
  type: reference
---

# ★★★ THE FactorC DIP IS **OURS**, and `FactorE X[0]` 12→0 IS **NOT** A NO-OP

## FactorC's X axis is VEHICLE SPEED at 64 counts/km-h
`X = [2240, 3840, 5120, 8960]` = **[35, 60, 80, 140] km/h**. (Same axis identified in
[[reference-accord-gp6a5e-is-speed-reclassifies-v44-v47]].)

**Stock mode-26 FactorC `Y = [0, 234, 429, 908]` — strictly monotone, NO dip.**

| build | `Y[0]` | dip vs `Y[1]`=234 |
|---|---|---|
| stock | 0 | — (monotone) |
| **V74** | **429** (`:= Y[2]`) | **−195** |
| **V75** | **566** | **−332** |

⇒ **the dip is ours.** It is a **descending ramp from 35 → 60 km/h**; all builds are identical above
60 km/h. Any "Honda shipped a non-monotone damper" reading is wrong.

## 🛑 Monotone at `C_Y0 = 566` is ARITHMETICALLY IMPOSSIBLE under the no-clip guard
Monotonicity needs `Y[2] ≥ Y[1] ≥ 566`. But at rate ≥ 4000 (`E = 927`), **any `C > 566` gives
`(C·927) >> 10 > 512`** — the ceiling floor
([[reference-accord-gp6ac2-is-a-backdrive-detector]]: the ceiling is pinned at **512**, never 1024).
**First offending speed: 80.5 km/h.**

★ **Reachable alternative — HALF-FILL: `[566, 429, 429, 908]`.**

| property | value |
|---|---|
| dip | **−332 → −137** |
| damping at 60 km/h / 21 °/s | **56 → 104 counts** |
| `k` | **unchanged** |
| guards | **passes every one** |

## ★ `FactorE X[0]` 12 → 0 is NOT a no-op
Below `X[0]` the evaluator clamps to `Y[0]` (= 0), so the *value* below the knee is unchanged — but
moving the breakpoint **left raises E across all of `[0, 200]`**: **196 of 4001 integer rate points
change.**

At the measured in-burst rate (**99 counts = 21 °/s**):

| quantity | before | after |
|---|---|---|
| dose | **137** | **147 (+7 %)** |
| `k` | 1.5798 | **1.4850 (−0.53 dB)** |

**Right direction on BOTH axes** — more dose at the operating point, *less* loop gain. **But far too
small to be a fault fix.**

⚠ It violates guard `E_X0_MIN_SAFE = 12`, whose own stated rationale (a steep ramp near zero)
**argues the wrong way**: `X[0] → 0` **REDUCES** the slope **2.867 → 2.695 per count**. The guard is
defending against something its own arithmetic says the edit improves — fix the guard's rationale before
citing it either way.

## ⚠ The ceiling on this whole family
`M = (C_Y0 · E_Y1) >> 10` is **capped at 297** (`C_Y0 ≤ 566` from the no-clip guard, `E_Y1` frozen)
⇒ `k = M / (X1 − X0)`, and **the best reachable at full plateau is `k = 0.7425`** — still **+2.15 dB
over V74**. So the FactorC/FactorE surface has real headroom left, but nothing like the **4.2 – 13.5**
the ratchet needs ([[accord-damper-fixes-the-grind-but-is-flat-on-the-ratchet]]).

Related: [[reference-accord-two-dead-zones-speed-and-rate]] ·
[[reference-accord-factore-x1-is-the-free-dose-lever]] ·
[[reference-accord-v74-v75-damper-is-a-sampled-relay]] ·
[[feedback-evaluate-clip-rules-on-the-observed-envelope]]
