---
name: reference-accord-damper-two-deadzones-factorC-factorE
description: The base-assist viscous damper (FUN_00034350 -> gp-0x6bd0) is a PRODUCT of 5 Q10 factors with TWO independent hands-off deadzones -- Factor C (driver torque) AND Factor E (motor rate). V44 opened only C, so E still zeroed it -> V44 failed. Real fix needs both.
metadata:
  type: reference
---

# Damper FUN_00034350 -> gp-0x6bd0 -- five factors, two deadzones (traced 2026-07-21, DampFactors)

> 🛑🛑 **SUPERSEDED IN THREE PLACES, 2026-08-06. Read [[reference-accord-two-dead-zones-speed-and-rate]]
> first — this file is kept for its factor-by-factor trace, not for its labels.**
>
> 1. **FACTOR C's AXIS IS VEHICLE SPEED, NOT DRIVER TORQUE.** The table below calls it *"`gp-0x6a5e`
>    voted driver torque"*. It is **voted vehicle SPEED**, at **64 counts per km/h**. [EVIDENCE, three
>    ways] `X = [2240, 3840, 5120, 8960] / 64 = [35, 60, 80, 140] km/h` — clean round numbers, which a
>    torque axis has no reason to produce; the friction lane's `X = [0, 1280, 5760] = [0, 20, 90] km/h`
>    uses the same cell and `build_v74_tva.friction_authority` names it *voted speed*; and on route 5d,
>    predicting V74's `bit7` with **speed** as FactorC's index agrees on **91.240 %** of 101,118 frames
>    versus **88.334 %** with `|driver torque|` — which cannot even reach the top two breakpoints
>    (`|tq|` max 4093 vs `X[3] = 8960`). ⚠ `gp-0x6a5e` is labelled "driver torque" in at least one other
>    memory (`reference_accord_setpoint_limit_15360_lerp`); **that labelling is unchecked, not
>    corrected here.** The golden model already has this right.
> 2. **THE MODE.** These are the **mode 10/11** records. The car is row 11 `TVCA4` running **mode 24
>    manual / 26 engaged**, so every lever aimed at 10/11 was inert by table selection —
>    [[reference-accord-car-is-tvca4-mode-24-26]], RULE 7.
> 3. **THE OUTPUT CLAMP IS EFFECTIVELY A CONSTANT 512.** *"DYNAMIC ±512..±1024 keyed on `gp-0x6ac2`"* is
>    true of the table and misleading in practice: `gp-0x6ac2` is a **sign-gated back-drive detector**
>    that reads **0** whenever the motion agrees with the command, so the LERP clamps flat to `Y[0]` and
>    **the ceiling is pinned at its 512 floor in ordinary driving**.
>    See [[reference-accord-gp6ac2-is-a-backdrive-detector]]. Size against **512**, never 1024.
>
> ✅ **What this file got RIGHT and is worth keeping:** the five-factor product, B and D dead-flat, and
> above all **"V44 opened only C, so E re-zeroed the product"** — the two-deadzone insight that V74
> finally acted on. V74 opened **both** and the damper measured live on-car for the first time:
> [[accord-v74-flew-damper-is-in-force]].

Corrects the earlier "product of four Q10 factors" record. It is **FIVE** factors, all Q10 (÷1024),
then a sign flip (`gp-0x6abe>0 → negate`, velocity-opposing), then a dynamic clamp:

| Factor | Axis | Table (m10/m11) | Stock Y | Hands-off/low-rate |
|---|---|---|---|---|
| A seed | `gp-0x698a` (MIN 1024) | — | ~1024 | usually unity |
| B | `gp-0x6bcc` driver-torque | 0xD2738/0xD274C | [1024,1024,1024,1024] | **FLAT — inert no-op** |
| C | `gp-0x6a5e` voted driver torque | 0xD27BC/0xD27D0 | [0,235,430,877] X=[2240,3840,5120,8960] | **0 below 2240** (V44 target) |
| D | `gp-0x6a10` angle-deviation | 0xD2774/0xD278C | [1024,1024,1024,1024] | **FLAT — inert** |
| E | `\|motor rate\|` `gp-0x6ac0` | 0xD27F8/0xD280C | [0,140,539,927] X=[60,400,2500,4000] | **0 below 60; 14% at 400** |

**Both C and E have Y0=0 → two independent hands-off deadzones.** V44 opened only C
([[v44-built-handsoff-damping]]); Factor E's motor-rate deadzone then re-zeroed the whole product at
low rate → V44 was doomed. The realistic hands-off term with only V44 applied is **7-32 counts**
(negligible vs the ~139-count ring). Factors B and D are dead-flat; not worth touching.

**Output clamp is DYNAMIC ±512..±1024** keyed on `gp-0x6ac2` (table 0xD209C/0xD20A8, X=[300,800]
Y=[512,1024], fallback cal 0xC6158=512) — NOT the flat ±2048 previously believed. Also small at low
rate, but it does not bind (product stays under 512 even aggressive).

**Manual rotation cures the vibration** because it drives `gp-0x6ac0` to its high-rate region (~900),
engaging the damper at ~160-213 counts — the authority target. V47 opens BOTH deadzones (Factor C =
V44's cells; Factor E reshaped Y0/Y1/Y2 → 700/750/800) to deliver that authority hands-off. See
[[project_v46_falsified_v47_dampers_only]]. Factor E has no interlock/float-mirror/monitor (int-only
lane) — safe to raise; but the OUTPUT CLAMP does, see [[reference-accord-damping-clamp-dtc1d-trap]].
