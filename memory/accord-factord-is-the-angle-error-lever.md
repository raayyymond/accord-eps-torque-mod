---
name: accord-factord-is-the-angle-error-lever
description: "🛑 TITLE CLAIM REFUTED 2026-08-09 — gp-0x6a10 is ABSOLUTE STEERING ANGLE, not a tracking error, and FactorD is structurally inert where the symptoms live because FactorC's zero dead zone precedes it. Read the top banner before citing anything here."
metadata:
  type: reference
---

> 🛑🛑 **HEADLINE REFUTATION, 2026-08-09 (late) — READ THIS BEFORE THE BANNERS BELOW.**
> **This file's own title claim and two of its load-bearing legs are REFUTED.** Kept in place rather
> than deleted, because the disassembly, the layout rule and the blast-radius work below are still
> correct and still useful. [EVIDENCE, route `6d` / `6e`]
>
> **(1) `gp-0x6a10` IS ABSOLUTE STEERING ANGLE, NOT AN ANGLE-TRACKING ERROR.** V84's `b4` rung is
> reproduced by the pure predicate `|steering angle| ≥ 0.85°` at **99.94%**; the step sits **exactly on
> the threshold's own numeric value**; and the relation holds in the **MANUAL** arm, where a *tracking*
> error is not even defined. ⇒ FactorD is a **steering-POSITION-scheduled gain**, in the same family as
> FactorC (speed) and FactorE (motor rate).
>
> **(2) ⇒ "THE ONLY FREQUENCY-SELECTIVE LEVER" IS REFUTED — THIS FIRMWARE HAS NONE.** The argument was
> *angle amplitude ∝ 1/ω, so a FactorD rising with angle error preferentially damps the low-frequency
> ratchet.* **That requires the axis to be the OSCILLATION amplitude. It is the WHEEL POSITION.**
> ⊕ **This also removes the standing argument that FactorE cannot do what FactorD can.**
>
> **(3) FactorD IS STRUCTURALLY INERT WHERE THE SYMPTOMS LIVE.** **FactorC multiplies in BEFORE
> FactorD** and has `X[0]` = 2240 counts = **34.97 km/h** with `Y[0] = 0`, in **all four** of this car's
> modes ⇒ **zero × anything = 0** below ~35 km/h, whatever FactorD holds. A third `gp-0x6a10` consumer —
> the boost LERP2 in `FUN_00034a72` — is **also** flat-zero in band0 (0–8 km/h) in all four modes.
> **Three independent confirmations.** Downstream consequence: `ch₀ = gp-0x6bd0` is **exactly zero on
> 98.8% of engaged frames on route `6e`**, which is why `0xC63A0` 1024→2048 is INERT.
>
> **(4) Table (b) — the 13-point `0xC6B66`/`0xC6B80` LERP — is DEAD as a shaped lever.** **88.6% of
> engaged driving sits in its flat first segment** ⇒ it delivers a near-constant **0.878× broadband
> trim**, the same class as V56's mute (null, cost damping) and the `0xC646C` work (null).
>
> ⇒ See [[accord-levers-killed-2026-08-09]] and
> [[accord-plant-model-residual-aggregator-chain]]. **Do not propose FactorD, or table (b), as a
> frequency-selective or shaped lever.**

> 🛑 **DISAMBIGUATION BANNER, 2026-08-09 (ghidra-factord, V86-prep session) — READ BEFORE CITING.**
> **Everything in this file is about ONE table: the mode-record FactorD family, `0xC9DB4[mode]`,
> n=5, `X=[0,50,100,150,700]`, flat `Y=[1024]×5`.** This is table **(a)**.
> There is a SECOND, physically separate `gp-0x6a10`-indexed table, table **(b)**: 13 points at
> `0xC6B66`(X)/`0xC6B80`(Y), inline inside `FUN_0003b8f6` (the 1 kHz plant-model observer V85 edited
> via `0xC40BC`), NOT mode-indexed, NOT flat (`Y` runs 899→1084, a real ~18% shaping curve). It shares
> only the index variable `gp-0x6a10` and the same `<0x2711` overflow-gate literal with table (a) —
> which is exactly what caused a same-day mix-up between two sessions reading this file. **Table (b) is
> documented separately** in
> `.claude/agent-memory/firmware-codepath-tracer/reference_accord_factord_six_family_map_and_1khz_lane_v84.md`.
> Confirm which table a claim is about before citing either file.
>
> ✅ **REINFORCED 2026-08-08 — THIS MEMORY IS CORRECT, AND HERE IS WHAT MAKES IT CHECKABLE.**
> FactorD is genuinely **flat unity**: `npt = 5`, `X = [0, 50, 100, 150, 700]`, `Y = [1024] × 5`,
> verified across **2,924 records (86 images × 34 modes)**. No build has ever moved a byte of it.
>
> 🛑 **THE LAYOUT RULE THAT PREVENTS THE RECURRING MISPARSE.** Record layout is
> **`X` at `base + 2`, `Y` at `base + 2 + 2·npt`** ⇒ **`+0x0A` for the 4-point FactorB/C/E, but
> `+0x0C` for the 5-point FactorD.** **A 4-point parse of FactorD misreads `X[4] = 700` as `Y[0]`** —
> which is exactly the shape of a confident wrong answer (a plausible non-unity Y row out of thin air).
> Anchor the offset on `npt`, never on a remembered constant.
>
> ★ **The excursion estimate, which changes the design.** Physics (angle amplitude ∝ 1/ω at fixed
> velocity amplitude) puts `gp-0x6a10` at **6.71 ct @27.75 Hz · 9.31 @20 Hz · 23.89 @7.79 Hz** — i.e.
> **the entire operating range sits inside the FIRST FLAT SEGMENT (`X[0]`=0 → `X[1]`=50).**
> ⇒ 🛑 **`X` MUST BE RESHAPED, NOT JUST `Y`.** A Y-only edit on the shipped breakpoints is a no-op for
> every symptom this kit has measured. *(This sharpens — and agrees with — the "likely deep in the flat
> segment" caveat below, and it is now a computed number rather than an inference from one datum.)*
>
> ✅ **Blast radius, and it is small:** the **sole reader of the FactorD table is `FUN_00034350`.** The
> other **seven** `gp-0x6a10` consumers read the **raw cell**, not the table ⇒ **a table edit is
> fault-isolated to the damper evaluator.** ⚠ `gp-0x6a10` is **word-aligned** and lockstep-shadowed at
> **`gp-0x4c90`** — see [[accord-lockstep-shadows-67fe-4c3a-and-6a10-4c90]] and
> [[accord-two-cave-encoding-traps-sar-floor-and-opcode-bit]] before probing it.
> ⊕ `gp-0x67fe`'s domain is exactly **{0,1,2}**, so gate #2 below needs **one** telemetry bit, not two.
> ⚠ And note [[accord-task5-is-100hz-damper-cannot-damp-21hz]]: FactorD rides the **100 Hz** evaluator,
> so above 25 Hz it is shaping an anti-damping term. Its value is at **7.79 Hz**, not at the ring.

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
