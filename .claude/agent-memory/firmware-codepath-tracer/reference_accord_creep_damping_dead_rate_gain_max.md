---
name: reference_accord_creep_damping_dead_rate_gain_max
description: At creep BOTH velocity-damping terms are architecturally off (FactorC Y[0]=0 zeroes the whole 5-factor product below 20/35 km/h; FUN_000456a4's gate needs ~212 deg/s) while the r24/r26 torque-derivative gain sits at its schedule MAXIMUM 3.000x (vs 2.10x at 100 km/h) — full speed-blend table addresses for gain_A/gain_B, and the lineage reason NOT to simply cut them
metadata:
  type: reference
---

Traced 2026-08-09 for the team-lead's low-speed 6-9 Hz ratchet brief (`EXCITATION-TRACER`), stock
`code.bin` in Ghidra + Python byte reads of stock and the V86B image.

> 🛑🛑 **SCOPE CORRECTION, same day — the "both dampers OFF at creep" headline is STOCK/MANUAL ONLY.**
> Flagged by `LOWSPEED-LANE-MAP` ([[reference-accord-lowspeed-gate-census-and-friction-5x-schedule]])
> and **re-verified by me directly** with a Python read of both images:
> ```
> FactorC mode 26 @0xD77D0  X=[2240,3840,5120,8960] = [35,60,80,140] km/h
>    stock Y=[  0,234,429,908]      V86B Y=[908,234,429,908]   (Y[0] @0xD77DA, 0 -> 908)
> FactorC mode 27 @0xD77E4
>    stock Y=[  0,233,426,875]      V86B Y=[875,233,426,875]   (Y[0] @0xD77EE, 0 -> 875)
> ```
> **V86B sets `Y[0]` EQUAL TO `Y[3]`** ⇒ below X0 the LERP clamps flat, so on V86B in the **engaged**
> modes 26/27 the table damper runs at **0.887× / 0.854× — its curve MAXIMUM — all the way to 0 km/h**,
> with a dip to 0.229× at 60 km/h (a non-monotonic U-shape). ⇒ **"the damper is off at creep" is TRUE for
> STOCK and for manual modes 24/25, FALSE for engaged on V86B.** Always state which **modes** and which
> **image** such a claim is scoped to. The `FUN_000456a4` comp-add half, and the whole r24/r26 half below,
> are unaffected — and the r24/r26 3.000× figure was independently corroborated by that session.

## ★★★★★ The creep asymmetry: damping dead, derivative gain maximal (STOCK / manual — see correction above)

**Both `-sign(rate)` terms are off at creep** [EVIDENCE]:
- `FUN_00034350` → `gp-0x6bd0`: output is a **PRODUCT** of FactorB..FactorE, and FactorC's `Y[0] = 0`
  with `X0` = 20 km/h (mode 0, `0xCE528`) / 35 km/h (mode 10, `0xD27BC`) ⇒ **term ≡ 0**, not "reduced".
  Runs at **100 Hz** (`FUN_00022ca0`), so it is also a poor place to *add* 8 Hz damping (phase lag).
- `FUN_000456a4` (comp-add, 1 kHz): gate `if not (thr < gp_6ac0): comp = 0` @`0x45780`; most permissive
  `thr` = 1000 ct ≈ **212 °/s** column rate at 4.7121 ct/(°/s). [INFERRED that creep is below it —
  `gp-0x6ac0`'s real counts during an event are UNMEASURED.]

**Meanwhile the r24/r26 derivative lane is at its maximum** [EVIDENCE, byte reads].

## The r24/r26 speed-blend gain schedule — full addresses

`FUN_0003ad74` (caller `FUN_00022ca0`, 100 Hz) blends 4 static records into 2 RAM gain tables consumed
at 1 kHz inside `FUN_0003aa2c`. Speed breakpoints `tp+0x7010` = **`0xC6010`** = `[0,640,3200,6400]` ct =
**[0,10,50,100] km/h** (64 ct/km/h). RAM consumers — **exactly one reader each**, full-opcode byte scan:
`gp-0x6e40`→`0x3AB9C`, `gp-0x6e38`→`0x3ABB4` (gain_B/r24); `gp-0x6e30`→`0x3AAD0`, `gp-0x6e28`→`0x3AAE4`
(gain_A/r26).

```
gain_A (r26, static)                      gain_B (r24, ptr array 0xCBF5C indexed mode*4)
  0 km/h 0xC6A68 Y=[3072,3072,2434,2048]    0 km/h  m24 0xD6A9C / m26 0xD7A88  Y=[3072,3072,2322,1536]
 10 km/h 0xC6A7C Y=[3072,3072,2488,1536]   10 km/h  m24 0xD6AD8 / m26 0xD7AC4  Y=[2560,2560,2246,1946]
 50 km/h 0xC6A90 Y=[2664,2664,2243,1436]   50 km/h  m24 0xD6B14 / m26 0xD7B00  Y=[2303,2303,2151,1947]
100 km/h 0xC6AA4 Y=[2560,2560,2145,1331]  100 km/h  m24 0xD6B50 / m26 0xD7B3C  Y=[2150,2150,2049,1947]
```
Q10, so **3072 = 3.000×**. Creep = **3.000×**, the schedule maximum (**1.43×** the 100 km/h value), and
**flat** across the whole small-signal rate index (0→400). Modes 24 and 26 are byte-identical here.
LERP struct `[count][X0..X3][Y0..Y3]`, Y row at `ptr+10`.

At 8 Hz the lane delivers **0.301·A** counts per A-count torque oscillation, at **+84.09° lead**
(N=4 backward difference, `0xC6C42`=4, −0.015 dB vs an ideal derivative) — the largest 8 Hz contribution
of any aggregator lane, ahead of `FUN_0003a382`'s 0.257·A.

## 🛑🛑 DO NOT reflexively cut the creep rows — the lineage points the OTHER way

- **V72 already flew this**: `gain_A` rec0/rec1 (`0xC6A72`, `0xC6A86`) → flat **512** (×0.25 r26 creep
  cut). **V83a restored them to stock 3072**; V86B carries stock. V72 is in the **"did NOT move grind #1"**
  row of `BUILD-LINEAGE.md`.
- **V62's `sar 0xa→0x9` DOUBLED both lanes flat** — and V62 **moved grind #1 by 8-42×**, the kit's first
  measured fix.
⇒ On-car, **doubling helped and cutting did nothing**: the +84° lead reads as **net-stabilising**
phase advance. The firmware alone cannot settle the sign; it depends on plant phase.
⚠ **But grind #1 is defined as the 18-22 Hz envelope.** The rate lane's creep dose is **UNTESTED at
6-9 Hz** — untested, not falsified.

## Related
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] — FactorC's Y[0]=0 floor.
[[reference-accord-fun456a4-gp6ad0-resolved-live-damping-no-step]] — the comp-add gate thresholds.
[[reference_accord_gp4f62_torque_rate_producer_and_c6c42_window]] — the N=4 derivative feeding r24/r26.
[[reference_accord_gp6b08_choke_point_and_shaper_consistency_monitor]] — where to filter, and why it bites.
