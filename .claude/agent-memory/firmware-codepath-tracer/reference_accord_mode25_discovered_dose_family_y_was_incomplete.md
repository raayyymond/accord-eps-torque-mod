---
name: reference_accord_mode25_discovered_dose_family_y_was_incomplete
description: The gp-0x63fd mode selector for THIS car's HW-ID row has FOUR values (24,25,26,27), not three -- found by scanning the FUN_00042746 row table directly (0xCD012+36*row) rather than trusting the inherited {24,26,27} DOSE_FAMILY_Y map. Mode 25 (Y[] at 0xD7A4C) has never been enumerated or dosed by any build. Mode 24=manual (established), mode 26/27=engaged; mode 25 shares mode 24's primary selector bit (gp-0x67f6=0) so is PLAUSIBLY also non-engaged but this is UNCONFIRMED. Blast radius on all 4 record addresses clean (Ghidra+Python LE, set-differenced, zero aliasing, zero direct code refs, sole access path is the 0xCBE74 pointer table).
metadata:
  type: reference
---

# Mode 25 discovered — `DOSE_FAMILY_Y` was incomplete, 2026-08-22

`dynamics-designer` task, final verification pass before cutting a `gp-0x6b26` build. Team-lead's own
byte read (modes 24/26/27) was correct as far as it went; this extends it by NOT inheriting the
`DOSE_FAMILY_Y = {24: 0xD6A6C, 26: 0xD7A5C, 27: 0xD7A6C}` map from `build_v100_tva.py` and instead
re-deriving the complete mode set from the selector mechanism itself.

## Method — read the selector's own row table, don't trust the inherited list [EVIDENCE]
`FUN_00042746` (the engagement re-selector, fresh decompile this session) picks one of 4 ROM columns
per HW-ID row: `(&DAT_0000e012)[row*0x24 + tp]` (i.e. `tp+0xE012+36·row` = `0xCD012+36·row`), keyed on
`(gp-0x67f6, gp-0x67e2)` ∈ {(0,1)→col0, (0,2)→col1, (1,1)→col2, (1,2)→col3}. Scanned all 4 columns for
rows 0-39, Python direct file read, `stock_fw_dump/code.bin`:
```
row 11: col0=24  col1=25  col2=26  col3=27   <- the ONLY row containing both 24 and 26 -> this car's row
(every other row is a different 4-tuple; rows 16+ read 0xFF/unused)
```
**This car's HW-ID row produces exactly {24, 25, 26, 27} — a 4-member family, not the 3-member
{24,26,27} the inherited build-script map assumed.**

## Mode 25's Y-table, dereferenced [EVIDENCE]
`0xCBE74` pointer array, slot for mode 25 = `0xCBE74+25*4=0xCBED8` → record base `0xD7A44` (count=3,
X=(0,1280,5760)), Y[] starts at **`0xD7A4C`**. Current value stock through V105 (checked both images):
**`(-9830,-5734,-1966)` — stock, never touched by any build.**

Full verified map (record base / Y[] start / current value):
```
mode 24 (manual)   0xD6A64 / 0xD6A6C   stock (-9830,-5734,-1966)   NEVER DOSED
mode 25 (unknown)  0xD7A44 / 0xD7A4C   stock (-9830,-5734,-1966)   NEVER DOSED
mode 26 (engaged)  0xD7A54 / 0xD7A5C   x1.5  (-14745,-8601,-2949)  dosed V91/V92+, on car since V96
mode 27 (engaged?) 0xD7A64 / 0xD7A6C   x1.5  (-14745,-8601,-2949)  dosed V91/V92+, on car since V96
```

## Mode 24 = manual, not exercised while engaged [EVIDENCE, prior kit memory + fresh cross-check]
[[reference_accord_mode24_mode26_stock_boost_friction_gainb_identical]] already establishes, for THIS
exact function/array (`FUN_00036c12`/`0xCBE74`), that mode 24=manual and mode 26=engaged, Honda ships
them byte-identical on stock. Cross-checked the MECHANISM independently this session via
`FUN_00042746`'s decompile: the re-selector fires on engagement-edge transitions (`gp-0x6806`≈latActive
crossing, `gp-0x69b0` engagement-gate sentinels `-0x8000`/`0`) — structurally consistent with the
24=disengaged/26=engaged identity, not an unrelated axis. ⇒ dosing mode 24 is inert for an
LKAS-engaged symptom and would instead change manual/LKAS-off steering feel — a real, separate,
unrequested consequence.

## Mode 25's role — flagged, NOT resolved [BELIEF]
Mode 25 shares `gp-0x67f6=0` with the confirmed-manual mode 24, differing only in `gp-0x67e2` (1 vs 2).
`gp-0x67e2`'s producer (inside the same `FUN_00042746`) appears to mirror a state at `gp-0x6733`,
gated by a threshold check against `cal(tp+0x7182)` — NOT traced further this session. Plausible
(same primary bit as manual) but UNCONFIRMED that mode 25 is also non-engaged. Do not dose it until
this is resolved.

## Blast radius, all 4 record addresses — Ghidra + Python LE, set-differenced, CLEAN [EVIDENCE]
Python LE32 scan: each record base (`0xD6A64`/`0xD7A44`/`0xD7A54`/`0xD7A64`) occurs **exactly once** in
the whole image, at its expected `0xCBE74` pointer-table slot — no aliasing pointer table found.
`search_instructions` on the same 4 addresses' text: all hits for `d6a6`/`d7a4` were branch-target text
collisions inside unrelated functions (`FUN_0000d61c`, `FUN_0003d4a2` — short local addresses like
`0x0000D6A6`, not the 20-bit targets `0xD6A64` etc.); `d7a5`/`d7a6` returned zero hits. **Both methods
agree: the sole access path to all 4 Y-tables is the `0xCBE74`→`FUN_00036c12` pointer indirection.**

## Consequence for the V106 build
Recommend dosing modes 26/27 ONLY (the confirmed-engaged pair) — leaves modes 24 and 25 untouched,
avoiding an unrequested manual-mode feel change and avoiding a dose on a mode whose role is unconfirmed.
This also removes the "unequal arms" complication a symmetric all-4-modes dose would have created.

## Related
[[reference_accord_mode24_mode26_stock_boost_friction_gainb_identical]] (the mode24=manual identity this
extends), [[reference_accord_r24_gainb_mode10_inert_and_24v26_array_diff]] (the sibling "wrong mode
index" trap this finding is the same class of check as),
[[reference_accord_gp6b26_v106_transfer_function_correction_and_disqualification]] (the build this
verification gates).
