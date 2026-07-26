---
name: reference_accord_c6518_lerp_readers_found_likely_thermal
description: The 0xC6518/0xC6534 "[0,10,25,50,80,120,200]" table IS live — a 7-point float LERP read by the FUN_00039702 monitor, keyed on gp-0x6d14. Ghidra reports ZERO xrefs (tp-relative misleading-zero). Axis is probably TEMPERATURE, not vehicle speed.
metadata:
  type: reference
---

# `0xC6518`/`0xC6534` — readers FOUND; axis probably thermal (2026-07-24)

Standing open item was "nobody ever found who reads `0xC6534`", with the `200` upper bound suspected
of being a 200 km/h speed clamp (the Honda Clarity EPS has an adjacent-u16 speed-validity window).
**Resolved: it is live, and the speed reading is probably wrong.**

## Structure [VERIFIED: Python byte read]

A LERP descriptor, not two loose arrays:
- `0xC6510` = `00 03 01 00` (flags/mode), `0xC6514` = `7` (u32 point count)
- `0xC6518` = X[0..6] float32 = `[0, 10, 25, 50, 80, 120, 200]`
- `0xC6534` = Y[0..6] float32 = `[12000, 10000, 10000, 7000, 7000, 7000, 7000]`
- `0xC6550` = `2`, `0xC6554..0xC6560` = `[300.0, 800.0, 0.5, 1.0]` (the known damping-clamp float
  mirror — a *different* table, do not run them together)

The exact 7-float axis byte pattern occurs **exactly once image-wide**.

## Readers [VERIFIED: raw byte scan + decompile, agreeing]

Inside `FUN_00039702` (body `0x39702-0x3a381`), a textbook clamp-then-walk LERP:

| PC | instruction | role |
|---|---|---|
| `0x39ffe` | `ld.w 0x7518[tp]` → `0xC6518` | X[0] low-clamp test |
| `0x3a02a` | `ld.w 0x7531[tp]` → `0xC6530` | X[6]=200.0 high-clamp test |
| `0x3a024` | `ld.w 0x7535[tp]` → `0xC6534` | Y[0]=12000 returned below range |
| `0x3a048` | `ld.w 0x754d[tp]` → `0xC654C` | Y[6]=7000 returned above range |

Axis input = `*(float*)(gp-0x6d14)` (`0xFEDF12EC`), which has exactly **one writer** — `st.w r6,
-0x6d14, gp` @`0x39538` in `FUN_000389ec` — and one reader @`0x3a002`. Producer is
`mulf.s r29, r10, r6`, i.e. a **product of two floats** (consistent with an ADC count × a scale
factor). A same-function sibling `gp-0x6ce8` @`0x3953c` = `(float)r16 * 0.1`.

## ⚠ Ghidra reports ZERO xrefs for all of them

`get_bulk_xrefs(["0xC6518","0xC6534","0xC6510","0xC6530","0xC654C"])` → **empty for all five**,
while the byte scan and the decompiler both show four live reads. Another instance of the recorded
tp-relative misleading-zero. Cross-check: the same scanner finds **6** readers of `0xC646C`
including `0x2a904`, the one `search_instructions` is on record for missing.

## Axis domain: probably TEMPERATURE, not vehicle speed [INFERENCE]

- The sibling LERP in the same function, `0xC6BA0` (13 pts), is X=`[0,34,64,85,100,120,140,157.6…]`
  → Y=`[0.878,0.887,0.958,1.0348,1.0573,1.0589…]` — a gain rising through 1.0, the classic shape of
  a **magnet-temperature Kt compensation** curve (flux falls with temperature ⇒ need more current).
- `0xC6518`'s breakpoints include **25**, the canonical calibration reference temperature, and `200`
  is a plausible max motor/ECU temperature; Y falling `12000 → 7000` reads as a **current/torque
  limit derate**, not a steering-assist speed curve.
- The axis is compared against `cal(0xC62D8)/64 = 3840/64 = 60.0` — a 60 °C decision point is
  ordinary; 60 km/h in a 12000→7000 assist limit is not.
- `FUN_00039702` is a **monitor**: ~12 channels built as `cal_offset(tp+0x7564…) + RAM(gp-0x6444…)`,
  each `/1024`, range-checked against the LERP output with a `-20.0` tolerance, packing fault bits
  into `gp-0x6924` and calling `FUN_000462e6(0x4377, …)`.
- This also explains the old negative result: arbitration genuinely does not read `0xC6534` because
  it belongs to a **thermal/plausibility monitor**, a different subsystem.

**NOT VERIFIED**: `r10`/`r29`'s provenance in `FUN_000389ec` was not traced. To settle the domain,
trace those two registers back to their ADC/CAN source. Until then treat "temperature" as a
well-supported inference, not a fact — and do **not** treat `0xC6530`=200.0 as a speed clamp.

## Related
[[reference_accord_can_rx_acceptance_filter_id_table_decoded]] — where vehicle speed actually
enters the ECU (CAN `0x1D0`/`0x158`), which is a different path from this table.
