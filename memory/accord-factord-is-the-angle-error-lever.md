---
name: accord-factord-is-the-angle-error-lever
description: FactorD is the only damper factor indexed by angle-tracking error rather than raw rate — untouched by every build, and the only lever that could cut damping exactly when LKAS needs rate.
metadata:
  type: reference
---

★★★★ **FactorD is the only factor in the damper chain indexed by something other than a raw rate, and no
build has ever written it.** It is the one structural candidate for serving "remove the grinding" and
"maximise LKAS angle rate" **simultaneously**, because the other levers are all rate-indexed and therefore
tax the very thing we want more of.

## The mechanics — all [EVIDENCE], fresh decompiles 2026-08-08

```c
// FUN_00034350, the damper evaluator (sole caller FUN_00022ca0)
if ((gp-0x67fe == 1 || gp-0x67fe == 2) && gp-0x6a10 < 0x2711 /*10001*/)
     FactorD = LERP(gp-0x6a10, (&PTR_0xC9DB4)[gp+0x63fd]);   // else UNITY (1024)
// the whole chain is a flat multiply, sign applied after, then clamp to +/- ceiling:
// product = ((((seed*B)>>10 * C)>>10 * D)>>10 * E)>>10
```
⇒ `Y < 1024` **reduces** the damper, `Y > 1024` **increases** it. No other sign interaction.

**The index, pinned:**
```
0x3fc8a-94:  gp-0x6a10 = abs( gp-0x69ca - clamp(gp-0x69e0 + gp+0x641c, +/- tp+0x733a) )
             then min(x, 0xFFFF)  <- a NO-OP; 0xFFFF exceeds any abs() of an i16
```
- **`gp-0x6a10` is an unsigned, UNCLAMPED angle-tracking-error magnitude at 0.1° per count.**
- `tp+0x733a` = **`0xC633A` = 130 = 13.0°**, and it clamps the *predicted* component only.
- **Scale anchored two independent ways, NOT from FactorD's own breakpoints** (the circularity that caused
  an earlier ×100 error on FactorC): `gp-0x69ca` sums at Q7 unity into `0x14A`'s `STEER_WHEEL_ANGLE`
  (opendbc −0.1 deg/count) via a pure byte swap, and `FUN_0003fd9c` carries the literal
  `(float)gp-0x69ca * 0.1`.
- Sole writers: `gp-0x69ca` ← `FUN_0003bd7c` @`0x3c09a` (angle accumulator) + a zero-reset;
  `gp-0x69e0` ← `FUN_0003f884` @`0x3fc08`. **Neither reads `gp-0x4f60` to produce its own value.**
- ⚠ Torque is not absent: inside `FUN_0003f884`, `gp-0x4f60` is an **additive** term on a sibling cell
  `gp-0x69c8` (`= gp-0x69ca + f(torque)`) which feeds `gp-0x69e0`'s next-cycle update. So `gp-0x6a10` is an
  **angle**-error magnitude one hop downstream of a torque-modulated predictor.

**The table (mode 24 and 26 identical, flat unity, n=5):**
| X (counts) | 0 | 50 | 100 | 150 | 700 |
|---|---|---|---|---|---|
| **= degrees** | **0°** | **5°** | **10°** | **15°** | **70°** |
| Y (stock, every mode) | 1024 | 1024 | 1024 | 1024 | 1024 |

The gate `gp-0x6a10 < 0x2711` = **< 1000.1°** is an overflow rail, not a real constraint.
Record `0xC9DB4[mode*4]`; mode-26 record at `0xD778C`, X at `0xD778E+2i`, Y at `0xD7798+2i`.

## 🛑 Two things must be measured BEFORE any FactorD edit

1. **`gp-0x6a10`'s actual excursion during a grinding episode — UNMEASURED.** If the symptom's own angular
   swing reaches the taper zone, then D and E both modulate at the oscillation's own frequency — less
   damping exactly at the amplitude peak — which **re-creates a relay on a new axis.** Same lesson as V80:
   *"stays in the flat zone" is not the same statement as "never enters the taper."*
   ⊕ The only angular datum on record is the 27.4 Hz event's steering angle **p-p 1.92°** — a *different*
   cell on the same sensor chain, so `gp-0x6a10` is expected to sit **low**. [BELIEF, not a measurement.]
2. **`gp-0x67fe` ∈ {1,2} is NOT settled.** The "1 in 100% of frames including disengaged" figure is a
   single V31P measurement that `HANDOFF-2026-08-01-grind2-…` explicitly re-opened —
   *"DISPUTED… unresolved, and unmeasured by V66… close it with a probe, not an argument."* V66 dropped the
   rung for budget. Structurally it needs `gp-0x6772 ∈ {4,5}` plus three further gates; `gp-0x6772`'s writer
   `FUN_0003d4a2` is a ≥15-state dispatcher, not decompiled. **If `gp-0x67fe` ever leaves {1,2}, FactorD is
   dead in those frames and the lever evaporates.** One telemetry bit closes it.

⇒ **Sequence a telemetry-only probe of both before building any FactorD edit.** See
[[accord-can-tx-gateway-whitelist-and-20-free-bits]].

## Candidate shape, if the measurement permits it

`gp-0x6a10` is an unsigned **magnitude**, so the shape wanted is monotonically **non-increasing in |error|**:
| X (°) | 0 | 5 | 10 | 15 | 70 |
|---|---|---|---|---|---|
| Y | 1024 | 1024 | 700 | 400 | 200 |

Full damping while tracking is tight; relief from 10–15°; floor by 70°. **Cuts damping only when the wheel
has drifted far from its predicted position, without touching the C×E product during ordinary holding.**
🛑 Compute the describing function of the **combined C×D×E product**, not FactorD alone, before building.

## Lineage: genuinely UNTESTED, not falsified

Zero hits as an edit target across every `build_v*_tva.py`. `FACTOR_D_PTRS` appears in V73–V77 **only inside
assert-untouched print loops**. `BUILD-LINEAGE.md` mentions `0xC9DB4` only in the structural description of
`FUN_00034350`. n=5 already — the only 5-point factor — so **no code edit is needed to use it**, unlike
B/C/E where the point count is pinned by hardcoded immediates. See
[[accord-stock-mode24-equals-mode26-damper-is-ours]].

## 🛑 Correction of record

`build_v30_tva.py` comments `gp-0x69ca` as **"driver torque."** That is **WRONG** — it is the angle
accumulator. The mislabel predates the angle chain being decompiled (2026-08-04) and was never re-verified.
