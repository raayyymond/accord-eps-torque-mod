---
name: reference_accord_d0xxx_lerp_bank_layout_and_pointer_indirection
description: The 0xD0000-0xD4000 LERP bank decoded — pointer targets the COUNT field, layout [count, X[count], Y[count]] int16; 4 per-variant banks 0x1000 apart reached ONLY via pointer tables in 0xC7xxx-0xCCxxx. Self-validated on the damper Factor E axis. Kills the "0xD07A4 = speed axis" reading.
metadata:
  type: reference
---

# `0xD0000-0xD4000` LERP bank — record layout + pointer indirection (2026-07-24)

## Record layout [VERIFIED: byte read, self-validated against a known table]

A pointer into the bank targets the **count field**, not a pad/flags word:

```
ptr -> [ count : int16 ][ X[0..count-1] : int16 ][ Y[0..count-1] : int16 ]
```

The int16 immediately *before* the count is padding/terminator (usually `0`), which is easy to
mistake for a leading flags field — it is not part of the record.

**Self-validation**: pointer slot `0xC9FAC` → `0xD27F8` decodes as `count=4`,
`X=[60, 400, 2500, 4000]`, `Y=[0, 140, 539, 927]`. That is **byte-identical** to the damper
**Factor E** motor-rate axis already recorded in
[[reference_accord_fun34350_damping_term_live_and_gated]] ("Q10 values 0→140→539→927 as rate climbs
60→400→2500→4000", "Y0=0 below 60 counts"). Layout confirmed by an independent prior finding.

## Four per-variant banks, reached ONLY by pointer indirection

Banks at `0xD0xxx / 0xD1xxx / 0xD2xxx / 0xD3xxx` are near-identical per-variant copies (`+0x1000`
stride). **`tp`-relative disp16 cannot reach any of them** (`tp=0xBF000`, so `0xD0000` is at
displacement `0x11000` — far past the signed-16-bit limit). Consequently:

⚠ **Any liveness test for a `0xD0xxx` address based on tp-relative reads, `mov imm32`, or Ghidra
xrefs returns a FALSE "dead".** Verified: **zero** `mov imm32` immediates land anywhere in
`0xD0000-0xD4000`. Access is exclusively:
1. a **u32 pointer** in a descriptor table in `0xC7xxx-0xCCxxx` (488 distinct targets found by a
   2-aligned LE32 scan — note a step-4 scan MISSES 2-aligned pointers), then
2. code materializing the descriptor **block base** with `mov imm32`, indexing by variant/mode.

Descriptor blocks are **`0xE8` bytes apart**; within a block, 3 consecutive u32 pointers form a
group for bank 0, the next 3 for bank 1, etc. Example: `0xC9DC4/C8/CC` → `0xD0774/078C/07A4`, then
`0xC9DD0/D4/D8` → `0xD1774/178C/17A4`.

## ★ `0xD07A4` is a damper factor, NOT a vehicle-speed axis — FALSIFIED

`0xD07A4` = `count=5`, `X=[0, 50, 100, 200, 400]`, `Y=[1024, 1024, 1024, 1024, 1024]`. It was
proposed as a speed-validity axis (`[0,25,50,100,200] km/h` under the Honda Clarity's 0.5 km/h unit,
terminating at the Clarity's 200 km/h `speed_clamp_hi`). **That reading is wrong:**

- Its pointer slot is `0xC9DCC` = `0xC9DB4 + 0x18`, and `0xC9DB4` is materialized by
  `mov 0xC9DB4, rX` @**`0x34596`**, which is inside **`FUN_00034350`** (body `0x34350-0x347b7`) —
  the base-assist **damping-factor producer**. [VERIFIED: `get_function_by_address(0x34596)`]
- The Factor E axis (`0xD27F8`, motor-rate **counts**) is consumed by the same function at `0x34624`
  (`mov 0xC9F84`; slot `0xC9F84+0x28 = 0xC9FAC`). Sibling axes in this bank are counts, not km/h.
- `Y` is **flat 1024 = unity Q10** ⇒ a no-op multiplicative factor in stock cal. This matches the
  already-documented 5th damping factor keyed on `gp-0x6a10`, recorded in
  [[reference_accord_no_speed_gain_in_baseassist_feedback_loop]] as "flat unity, no-op".
- A validity window would be a two-sided compare yielding a boolean; this is a LERP. Wrong shape.

**General lesson**: `400` in this bank is not diagnostic of speed. The bank mixes torque-count axes
(`0xD0102`-family, X up to 12000) and motor-rate-count axes (`0xD27F8`, X `60..4000`), and `400`
appears in both. Classify by **consumer function**, not by constant value.

## ⚠⚠ The SAME record layout exists in the tp cal window — "adjacent int16 pair" is a TRAP there too

The `[count][X[count]][Y[count]]` layout is **not confined to `0xD0xxx`**. Worked example that
falsified a promising candidate: `0xC697C`=10 and `0xC697E`=255 look like a perfect `(lo,hi)` pair —
both live, read by back-to-back instructions `0x29c74`/`0x29c6e` inside the `STEER_STATUS`
arbitration function, with `10` matching a measured ~3.1 mph lockout edge under 0.5 km/h units.
**All of that is coincidence.** Disassembly (`disassemble_bytes dry_run`) shows:

```
0x29c5a  movea 0x7974, tp, r9     ; r9 = table base 0xC6974
0x29c5e  ld.hu 0x7976, tp, r7     ; X[0] = cal(0xC6976) = 4
0x29c6a  cmp r7, r13 ; bh         ; below-range clamp
0x29c6e  ld.hu 0x797e, tp, r6     ; -> Y[0]  = cal(0xC697E) = 255
0x29c74  ld.hu 0x797c, tp, r16    ; X[last] = cal(0xC697C) = 10
0x29c7a  bnc -> 0x29c86           ; above-range clamp
0x29c86  ld.hu 0x7984, tp, r6     ; -> Y[last] = cal(0xC6984) = 0
         ...sld.hu 0x2,ep walk loop...
```

So `0xC6974`=count 4, X=`[4,6,8,10]`, Y=`[255,…,0]`; `10` is **X[last]** and `255` is **Y[0]**.
Input is `ld.bu -0x6830, gp` — a **byte**, not a speed. **Rule: never promote an adjacent-int16 pair
to a "clamp pair" without disassembling the load site.** A `movea <disp>, tp, rN` a few instructions
earlier is the tell that you are looking at a table base, not two scalars.

## Related
[[reference_accord_c6518_lerp_readers_found_likely_thermal]] — the parallel float-LERP family in the
tp-addressable cal window, whose `200.0` was likewise mis-read as 200 km/h.
