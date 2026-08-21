---
name: accord-honda-biquad-arm-gate-is-false-on-this-car
description: "🛑🛑★★★★★ `gp-0x671a < 5` MEASURED on-car (route 59) ⇒ Honda's own arm gate for the FUN_000352b4 biquad (`cal(0xC64FA)=5 <= gp-0x671a`) is FALSE. Setting `0xC649B` 0→1 ALONE is a GUARANTEED NULL. V103's source repoint to gp-0x6806 was LOAD-BEARING, not cosmetic."
metadata:
  node_type: memory
  type: reference
---

# Honda's biquad arm gate is FALSE on this car — arming by cal alone is a guaranteed null

**Established 2026-08-21, from a flown probe, not from static analysis.**

## The gate
`FUN_000352b4`'s dormant 2nd-order section is armed only when **both**:
```
cal(0xC649B) == 1                 # stock = 0x00  -> the "arm byte"
cal(0xC64FA) <= gp-0x671a         # cal(0xC64FA) = 5   [EVIDENCE, byte-read stock]
```
Gate structure pcode-confirmed: `analyze_dataflow` backward from `0x35a12` resolves the
`cmp r12,r9` + `setfnc` idiom to **INT_LESSEQUAL**, inputs `[cal(0xC64FA), gp-0x671a]`, feeding the
CBRANCH at `0x35a26`.

## 🛑 THE MEASUREMENT — `gp-0x671a < 5` ON THE CAR
Recovered from **V72's flown cave on route `59`** (87,940 frames, `_cache_r59/r59s*.npz`), where
`bit6 = gp-0x69a4 >= 512` and `bit5 = gp-0x69a4 >= 1024`. Measured on-car: **bit6 = 200, bit5 = 0.**

`gp-0x69a0` (the assist-map slope limiter) is selected in `FUN_00035b20` from one of two speed tables
by `bVar1 = gp-0x671a < cal(0xC64FA)`:

| branch | condition | Y knots | max reachable `gp-0x69a4` | predicts bit6 |
|---|---|---|---|---|
| **tblB** | `gp-0x671a >= 5` | [358, 307, 307, 307] | **358** | **0** — `>= 512` structurally impossible |
| **tblC** | `gp-0x671a < 5` | [358, 358, 461, 512] @ [5,25,50,70] km/h | **512** above 70 km/h | **200** |

The reconstruction predicted **200 under tblC and 0 under tblB**. The car returned **200**.
⇒ **`gp-0x671a < 5` on route `59`** ⇒ **Honda's arm condition `5 <= gp-0x671a` is FALSE.**

## CONSEQUENCES
1. 🛑 **Setting `0xC649B` 0→1 alone is a GUARANTEED NULL.** The `AND` never closes. Any future build
   that "arms the biquad" by the calibration byte alone will fly, fault-free, and change nothing.
2. ⭐ **V103's 3-instruction repoint was LOAD-BEARING, not a refinement.** `0x35A06`
   `ld.bu -0x671a[gp],r9` → `ld.bu -0x6806[gp],r9`; `0x35A12` `cmp r12,r9` → `cmp r0,r9`;
   `0x35A18` `setfnc r6` → `setfne r6`. It replaced a dead condition with `gp-0x6806 != 0` (latActive),
   which is what actually put the filter in force — engaged-only. **First on-car confirmation.**
3. ⊕ **It retires a probe rung retroactively.** V72's `bit6` was **structurally dead under tblB** and
   fired only because tblC was live — a bit spent on a threshold whose reachability was never checked.
   See [[feedback-size-probe-rungs-against-lane-reachable-output]].

## Method note — why this is EVIDENCE and not inference
The 200/200 count match was produced by a from-ROM reconstruction of the assist map
(`analysis-2020accord/assist_map_mirror.py`) that was **not fitted to this cell**. It is a simultaneous
test of the mode-record decode, the speed interpolation, the axis orientation, the
`0.388·(A − 0.0912·B)` transform, the `cal(0xC6178)=5274` ceiling, the map build, the `gp-0x69a0`
slope limiter, the breakpoint search, the slope-vs-value register split, and the ×1.024 wire scale.
Any one of those wrong and the count is not 200. Frame-level overlap 180/200 (the ±20 is 100 Hz
resampling slop against a 1 kHz signal).

⚠ **Residual:** `gp-0x671a < 5` is proven *at the 200 firing frames*. The exact total-count match
argues it held for the whole drive, but it has not been shown frame-by-frame elsewhere, and it has not
been re-checked on a route other than `59`. `gp-0x671a`'s producer is `FUN_000428d4` (writes at
`0x42a12`; 8 gp-relative accesses image-wide).

## Related
[[accord-v103-biquad-armed-engaged-only]] · [[feedback-size-probe-rungs-against-lane-reachable-output]] ·
[[accord-v64-null-is-on-the-gate]] — the same failure class: the null was on the gate, not the
hypothesis. This memory exists so that mistake is not made a third time on this specific filter.
