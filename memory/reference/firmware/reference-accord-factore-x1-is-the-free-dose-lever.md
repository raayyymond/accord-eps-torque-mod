---
name: reference-accord-factore-x1-is-the-free-dose-lever
description: FactorE X[1] is the damper's free dose lever -- moving the knee LEFT raises dose at the symptom's operating point without raising the plateau that sets the surface maximum, so it cannot breach the 512 ceiling. FactorE Y[] has only 1.318x of verified headroom; FactorC has ZERO.
metadata:
  type: reference
---

# ★★ `FactorE X[1]` is the FREE dose lever — `FactorE Y[]` and `FactorC` are already at their caps

Priced on route 5d's own measured (speed, rate) distribution, against V74 as flown.

## The arithmetic
On the live engaged mode 26, `FactorB` and `FactorD` are flat 1024 and the seed is pinned 1024, so

> **`dose = (FactorC(speed) × FactorE(rate)) >> 10`**, clamped to `ceiling(gp-0x6ac2)`

V74 as flown: `FactorC Y = [429, 234, 429, 908]` (429 at creep) ·
`FactorE X = [12, 400, 2500, 4000]`, `Y = [0, 539, 539, 927]`.

```
E(r) = 0                       r <= 12
     = 539*(r-12)//(400-12)    12 < r < 400        <- THE RAMP. The symptom lives here.
     = 539                     400 <= r <= 2500    <- the plateau
dose(creep, r) = (429 * E(r)) >> 10
   r =  15 cts ( 3.2 deg/s): E=  4 -> dose    1     <- the FIRST non-zero dose
   r =  99 cts (21.0 deg/s): E=120 -> dose   50     <- the ratchet's own operating point
   r = 127 cts (27.0 deg/s): E=159 -> dose   66     <- the 6-9 Hz arm
   r >= 400                 : E=539 -> dose  225     <- the plateau
```

🛑 **The effective dead zone is `r >= 15`, not `X[0] = 12`** — the `>>10` truncation needs
`E >= ceil(1024/429) = 3` before the dose is even 1 count. **Moving `X[0]` below 12 buys nothing**, and
the build already flagged that band as the not-to-fly-without-telemetry hazard zone.

## THE CEILING IS 512, NOT 1024 — and that is what caps `Y`
`ceiling = LERP(gp-0x6ac2, 0xC77A0[mode*4])`, `X=[300,800] Y=[512,1024]`, all 26 modes identical. Because
`gp-0x6ac2` is a **sign-gated back-drive detector** and reads 0 in ordinary driving
([[reference-accord-gp6ac2-is-a-backdrive-detector]]), the ceiling is **pinned at 512**. So the real
no-clip constraint is `(FactorC_creep × FactorE Y[3]) >> 10 ≤ 512`:

| `Y[1..3]` × k | dose @ r=99 | unclamped peak `(429·Y[3])>>10` | |
|---|---|---|---|
| 1.0 (V74 as flown) | 50 | 388 | ✅ |
| **1.318** | 66 | **511** | ✅ **THE CAP** |
| 1.5 | 75 | 582 | ❌ clips |
| 2.0 | 100 | 776 | ❌ |
| 3.0 | 151 | 1165 | ❌ |

⇒ **`FactorE Y` has only 1.318× of verified headroom** — worth 50 → 66 at the operating point.
🛑 Above it the high-rate corner clips, reintroducing exactly the saturation nonlinearity the build's cap
was written to prevent.

## ★ THE FREE LEVER: move `X[1]` LEFT. `Y` untouched ⇒ the cap CANNOT be breached
The peak stays `(429 × 927) >> 10 = 388` for **every** `X[1]`, because only the ramp's slope changes:

| `X[1]` | dose @ r=99 | vs V74 | ramp slope (E per rate-count) | peak |
|---|---|---|---|---|
| 400 (V74) | 50 | 1.00× | 1.39 | 388 ✅ |
| 300 | 67 | 1.34× | 1.87 | 388 ✅ |
| **200** | **104** | **2.08×** | 2.87 | 388 ✅ |
| 150 | 142 | 2.84× | 3.91 | 388 ✅ |
| 100 | 222 | 4.44× | 6.12 | 388 ✅ |

`X[1] → 200` lifts engaged-creep mean dose **52.2 → 79.8** and frames ≥ 43 counts from **38.6 % → 52.4 %**
on route 5d's distribution, **with the surface maximum unchanged**.

⚠ **[BELIEF] The tradeoff is PHASE, not magnitude.** A 2–4× steeper low-rate ramp is the hazard
`builds/v50_v79/build_v74_tva.py` flags (`X0 < 30 with Y1 > 300`: the ramp starts near zero *and* is steep). That is a
**GATE 2** question and **cannot be settled from a log** — it needs the closed-loop magnitude *and* phase
argument in every loop the signal is in.
✅ What *is* settled: `Y[0] = 0` is preserved either way, so magnitude still vanishes with rate and the
bare `sign()` relay multiplies a vanishing quantity ⇒ **no discontinuity, no chatter mechanism** — the
property that distinguishes this family from V72's flatten-to-relay error.

## `FactorC` has ZERO headroom
V74 already set mode-26 `C Y[0] := Y[2] = 429`, which *is* the derived cap:
`(429 × 927) >> 10 = 388 ≤ 512` ✅ but `(908 × 927) >> 10 = 821 > 512` ❌. Raising `Y[0]` toward `Y[3]`
would be 2.12× at creep and **saturates at high rate**.
⊕ The edit left the row **non-monotone** — it dips to 234 at 3840 counts (60 km/h) before rising to 908 —
and route 5d shows that dip on-car as an engaged bit7 trough of **18.96 %** in the 50–65 km/h band against
39.93 % at 35–50.

Related: [[accord-v74-flew-damper-is-in-force]] · [[reference-accord-two-dead-zones-speed-and-rate]] ·
[[reference-accord-gp6ac2-is-a-backdrive-detector]] · [[reference-accord-rate-scale-4p7121-stands]] ·
[[feedback-evaluate-clip-rules-on-the-observed-envelope]] ·
[[feedback-cave-two-gates-ram-ownership-and-closed-loop]]
