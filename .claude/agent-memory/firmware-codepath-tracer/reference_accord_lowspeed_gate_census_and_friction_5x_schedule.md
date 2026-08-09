---
name: reference-accord-lowspeed-gate-census-and-friction-5x-schedule
description: Complete low-speed (0-15 km/h) operating-point map of the assist chain — every speed gate with km/h thresholds, per-lane active/gated census, and the finding that the friction lane gp-0x6b26 is 5.00x stronger at 0 km/h than at 90 km/h and 5x closer to its clamp rail (the steepest speed schedule in the firmware).
metadata:
  type: reference
---

Produced 2026-08-09 for the low-speed filter-placement brief (`LOWSPEED-LANE-MAP`). Ghidra = stock
`code.bin`; all "current" values Python-read from
`_v86b_FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin` (sha256 `b2dfe9ff…`).
Speed axis is **64 ct/km/h** everywhere — re-validated three ways this session (`0xC62EA`=320→5.00,
`0xC6316`=640→10.00, FactorC X[0]=2240→35), all matching the anchors exactly.

## ★★★★★ The friction lane is the creep amplifier — 5.00x, and it can only saturate at creep

`FUN_00036c12` → `gp-0x6b26`. Its entire gain is a **3-point speed LERP**, `(&LAB_000cbe74)[mode]`
(m24 ptr `0x0D6A64`). **Identical in modes 24/25/26/27, and STOCK == V86B** — never touched by any build.

```
X = [0, 1280, 5760] ct = [0, 20, 90] km/h
Y = [-9830, -5734, -1966]
gp-0x6b26 = clamp( ((i16(gp-0x6c2c) * Yspd) >> 6) * 0x111 >> 0x12 , +/- cal 0xC407E=511 )
```
```
 km/h   Yspd    gain     x vs 90km/h   |gp-0x6c2c| to hit the +/-511 rail
    0  -9830  -0.15995      5.00               3195
    8  -8192  -0.13330      4.17               3833
   15  -6758  -0.10997      3.44               4647
   20  -5734  -0.09330      2.92               5477
   90  -1966  -0.03199      1.00              15973
```
Two consequences, both structural:
1. Input is **`gp-0x6c2c`, the motor-rate derivative** (not driver torque) ⇒ this is already a
   rate-domain path into the aggregator, 1 kHz (`FUN_0002214a`).
2. **The ±511 rail is 5x closer at 0 km/h than at 90.** A lane that clips is a relay ⇒ harmonics and
   limit-cycle support. This is a mechanism for creep-only "grinding" that needs no speed-dependent
   plant story. [EVIDENCE for gain/clamp/ratio; **BELIEF** that it reaches the rail on-car — needs a
   real `gp-0x6c2c` excursion measurement.]

🛑 **Biggest way this is wrong:** the table is only used if `gp-0x671a < cal 0xC64FD (=5)`; otherwise the
gain is scalar `0xC640A` = 57344, and if `gp-0x671a == 0xFF` or `gp-0x67f4 != 1` it is `0xC640C` = 62259.
`gp-0x671a`'s creep-time value is NOT established. Check it before building on the 5x.

## Speed-gate census (stock → V86B)

| gate | addr | stock | V86B | threshold | effect |
|---|---|---|---|---|---|
| low-speed steer lockout | `0xC62EA` | 320 | **0** | 5.00 → **0** km/h | disabled since V53; LKAS commandable at 0 km/h |
| CAN-commanded assist shutdown | `0xC62EE` | 320 | 320 | 5.00 km/h | live |
| governor speed | `0xC6316` | 640 | 640 | 10.00 km/h | |
| FactorC damper axis X[0] | table | 2240 | 2240 | 35 km/h | |
| rate-lane speed bins | `0xC6010`-`0xC6016` | 0/640/3200/6400 | same | 0/10/50/100 km/h | `FUN_0003ad74` |
| speed fallback if invalid | `0xC6314` | 5120 | 5120 | 80 km/h | used when `gp-0x67f4 != 1` |
| boost speed LERP | `0xCA154[mode]` | X=0..10240 | same | 0/10/40/80/122/160 km/h | |
| friction speed LERP | `0xCBE74[mode]` | X=0/1280/5760 | same | 0/20/90 km/h | the 5x lane |
| `FUN_0003aff4` LERP | `0xC6A4A`/`0xC6A58` | X=0..14720 | same | 0/10/25/50/80/120/230 | Y=[0,0,0,1,3,6,16] — **zero below 50 km/h** |
| monitor arm speed | `0xC62E2` | 0 | 0 | 0 km/h | **threshold is 0 ⇒ never blocks** (matters for `FUN_00036388` and `FUN_00035e00`) |
| speed range rail | literal `0x7D01` | — | — | 500 km/h | overflow guard |

## Per-lane state at 0-15 km/h

**Nothing is gated OFF at creep except Honda's own table damper.** Three lanes are actively STRONGER there.

| lane | cell | producer | at creep | creep/highway |
|---|---|---|---|---|
| base assist / peak-hold | `gp-0x6b86` (±12288) | `FUN_000352b4` | ACTIVE, **no `gp-0x6a5e` read** | see caveat |
| boost | `gp-0x6bbe` (±512, `0xC7970` flat) | `FUN_00034a72` | ACTIVE 0.539 | 1.23x (peak 0.644 @40 km/h) |
| table damper | `gp-0x6bd0` | `FUN_00034350` | manual **ZERO**; engaged-on-V86B **0.887** | — |
| r24 / r26 | inline (±8192) | `FUN_0003aa2c`, gains `FUN_0003ad74` | ACTIVE, **at max** 3072 | **1.43x** vs 2150 @100 |
| friction | `gp-0x6b26` (±511) | `FUN_00036c12` | ACTIVE, **at max** | **5.00x** |
| return-centre | `gp-0x6b62` | `FUN_00036388` | ACTIVE (`0xC62E2`=0 ⇒ leg never fires); slew ±1/cycle ⇒ ≤20 ct pk @7.8 Hz | — |
| aggregator / governor / comp-add / shaper | — | `FUN_0003aa2c` / `FUN_0004503c` / `FUN_000456a4` / `FUN_00042af8` | all ACTIVE, no creep gate | — |
| 1 kHz plant model | `gp-0x6bfc` | `FUN_0003b8f6` | ACTIVE, **no speed term at all** | — |

**Task split matters for filter placement:** friction, rate lanes, aggregator, governor, comp-add,
shaper and the plant model are all **1 kHz** (`FUN_0002214a`); **only boost and the table damper are
100 Hz** (`FUN_00022ca0`). An 8 Hz filter must not go in the 100 Hz task.

## 🛑 The base assist has NO `gp-0x6a5e` dependence — verified zero, but a bounded claim

[EVIDENCE, two methods] `FUN_000352b4` (`0x352B4`-`0x35E00`) has **zero** `gp-0x6a5e` accesses:
Ghidra `search_instructions` → 0 in range, AND an independent raw Python LE scan (disp16 form
`hw2 = 0x95A2`/`0x95A3` with base-reg field == r4, plus the 6-byte extended form) → 0 in range. Same for
`FUN_000389ec` and `FUN_00039702`. The raw scan found **54 image-wide hits vs Ghidra's 48** — a fresh
instance of the documented undercount — extras at `0x2B0B6`, `0x2B214`, `0x2B2CE`, `0x4C830`, `0x4CAD8`,
`0x53E6A` (unadjudicated, none in the ranges the conclusion rests on).

[**BELIEF, NOT established**] that the base assist is speed-flat overall. Its 10-point curve lives in RAM
at `gp-0x6444`(X)/`gp-0x6430`(Y) and **the writer was not found** — all access is `ep`-relative
(`movea -0x6444,gp,ep` @`0x35378`,`0x42CAE`; `movea -0x6430,gp,ep` @`0x39B22`,`0x42B42`,`0x42DD0`), and
`sst`/`sld` through `ep` is invisible to an operand scan. It could still be scheduled by another cell —
`gp-0x6a62` is the prime suspect (`FUN_00034a72` uses it with breakpoints `[0,640,2560,5760,6400]`, the
same 64 ct/km/h shape). **Do not build on "the base assist is speed-flat" until that writer is found.**
⚠ `FUN_00039702` is a **plausibility MONITOR** on those arrays (float tolerances `tp+0x7564..0x758a`,
fault word `gp-0x6924`, `FUN_000462e6(0x4377,…)`), not their builder — easy to mistake for one.

## 🛑 Reconciliation with `EXCITATION-TRACER`'s same-session memory

[[reference_accord_creep_damping_dead_rate_gain_max]] (written the same day) states "at creep BOTH
dampers are architecturally OFF while r24/r26 sits at its schedule MAX 3.000x". **The r24/r26 half is
independently corroborated here** — I read `0xCBF5C[24]`/`[26]` → `Y[0]=3072` = 3.000x, byte-identical
stock↔V86B, and 2150 at the 100 km/h bin ⇒ 1.43x. **The "both dampers OFF" half is true for STOCK and
for manual modes 24/25 on V86B, but FALSE for the ENGAGED case on V86B**, where `0xD77DA`/`0xD77EE` set
FactorC `Y[0]` = 908/875 ⇒ the table damper runs at 0.887 of its highway value all the way to 0 km/h.
Read the two memories together, and always check which modes and which image a "damper is off at creep"
claim was scoped to.

## Function-identity corrections worth keeping
- `FUN_000352b4` = the **base-assist / peak-hold** lane (10-pt |torque| curve → `gp-0x6b86`, ±0x3000, the
  largest aggregator clamp). Not merely "peak-hold".
- `FUN_0003ad74` = the **r24/r26 speed-bin curve BUILDER** (writes `gp-0x6e40`/`gp-0x6e38` and
  `gp-0x6e30`/`gp-0x6e28`), fed by mode-indexed sets `0xCBF5C`/`0xCC044`/`0xCC12C`/`0xCC214` and fixed sets
  `0xC6A68`/`0xC6A7C`/`0xC6A90`/`0xC6AA4`.
- **Two different things are called "friction":** the aggregator lane `gp-0x6b26` (`FUN_00036c12`,
  speed-scheduled, this file) and the Path-2 plant-model term in `FUN_0003b8f6`. `0xC40BC`
  (600→**6000** on V86B, from V85) has **exactly one reader, `FUN_0003b8f6` @`0x3BAB4`** — it is the
  *plant-model* friction, has **no speed term**, and is in force identically at creep and highway.

## Related
[[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]] — same function, the no-stick-slip result;
this file adds its speed schedule, which that memory did not have.
[[reference_accord_friction_lane_c407e_census_and_mode26_record_identity]] — `0xC407E`=511 is the clamp
used above. [[reference_accord_gp6c2c_transfer_function_triple_verified]] — the lane's input.
[[reference_accord_factord_six_family_map_and_1khz_lane_v84]] — FactorC's 35 km/h floor.
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] — the damper product.
[[reference_accord_low_speed_lockout_window_c62ea]] — `0xC62EA`, here confirmed = 0 on V86B since V53.
