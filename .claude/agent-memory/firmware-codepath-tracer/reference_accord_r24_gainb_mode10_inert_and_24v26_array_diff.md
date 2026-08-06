---
name: reference_accord_r24_gainb_mode10_inert_and_24v26_array_diff
description: 🛑🛑🛑 CRITICAL — every r24 gain_B table edit since V69 (V69/V70/V71A/V72/V73) targeted mode-INDEX 10's records, but this car's live mode is 24 (manual)/26 (engaged) — confirmed byte-exact via LE32 literal scan, those edits are structurally INERT. Full mode-proof-vs-mode-indexed split for every rate-lane lever. Plus: diffed 21 mode-indexed arrays at index24 vs 26 — only 2 of 21 differ.
metadata:
  type: reference
---

**Entry point & goal**: after [[reference_accord_gp63fd_full_enumeration_writers_and_13_reader_arrays]]
and the team-lead's correction that live modes are 24/26 (not 8/10, aliased under a 4-bit probe field),
verify whether V62-V73's rate-lane (r24/r26) edits actually land on the live car. [EVIDENCE throughout.]

## 🛑🛑🛑 r24 gain_B table edits (V69/V70/V71A/V72/V73) are INERT on this car
LE32 literal scan of `stock_fw_dump/code.bin` for the addresses every one of those builds edits:
`0xD2A74`→exactly 1 hit at `0xCBF84`; `0xD2AB0`→exactly 1 hit at `0xCC06C`. Both are `LAB_000cbf5c`/
`LAB_000cc044` + `10*4` — **index 10**. Decoded both 34-entry pointer arrays fully (groups-of-3 variant
structure, e.g. idx4-6→`0xD0A7x` family, idx7-9→`0xD1A7x`, idx10-12→`0xD2A7x` [the edited one],
idx22-24→`0xD6A7x`/`0xD6A9x`, idx25-27→`0xD7A7x`/`0xD7A8x`): **index24→`0xD6A9C`/`0xD6AD8`,
index26→`0xD7A88`/`0xD7AC4` — different addresses entirely.** `0xD2AEC`/`0xD2B28` (the "highway,
deliberately untouched" pair) are the SAME index-10 family, same problem. **Every r24 gain_B table
edit V69 through V73 (V73's `V72_LEVER_A` cites the same addresses) never reached this car's live
calibration path.**

## r24/r26 producer, address-pinned [EVIDENCE, fresh decompile+disasm `FUN_0003aa2c`, 0x3aa2c-0x3ad73]
- **r24 = `gp-0x6ada`** (`st.h` @`0x3ad5a`): LERP over `gp-0x6e40/38/3a/32/3e` (MODE-INDEXED, from
  `FUN_0003ad74`'s first block: `LAB_000cbf5c`/`LAB_000cc044`/`LAB_000cc12c`/`tp+0xd214`, `mode*4`)
  **× scalar gain, selected by `gp-0x671d`: `0xC6442`(tp+0x7442) if !=0, else `0xC6446`(tp+0x7446) or
  `0xC6440`(tp+0x7440) depending on `lp`/`r2` flags** — `sar 0xa,r8 @0x3ac20` normalizes the product.
- **r26 = `gp-0x6adc`** (`st.h` @`0x3ad4e`): LERP over `gp-0x6e30/28/2a/22/2e` (FIXED, from
  `FUN_0003ad74`'s SECOND block — literal `tp+0x7a68/7a7c/7a90/7aa4`, NEVER mode-indexed) **× scalar
  `0xC643E`(tp+0x743e) or `0xC6444`(tp+0x7444) depending on `bVar1`/`bVar4`** — `sar 0xa,r6 @0x3ab76`.
- `0x3AA96` (the gate byte V67/68/71C/... move): confirmed CODE — repoints an `ld.bu` displacement
  field from dead cell `gp-0x683c` to `gp-0x6806` (≈latActive). One byte inside an instruction.

## The mode-proof / mode-indexed split for every named rate-lane lever
| lever | address(es) | builds | mode-proof? |
|---|---|---|---|
| r24 gain_B table | `0xD2A74`/`0xD2AB0`/`0xD2AEC`/`0xD2B28` | V69,V70,V71A,V72,V73 | ❌ **INERT — wrong mode index** |
| r24 scalar arm | `0xC6446` | V67,V68,V71C,V72 | ✅ single tp-relative scalar |
| r26 scalar arm | `0xC6444` | V71C | ✅ single tp-relative scalar |
| gate repoint | `0x3AA96` | V67,V68,V71C (reverted V69-72) | ✅ code, instruction displacement byte |
| sar 0xa→0x9 ×2 | `0x3AB76`(r26) / `0x3AC20`(r24) | V62 (reverted V66; V71A r26-only) | ✅ code |
⇒ **V71C-vs-V72's grind #2 contrast is a CLEAN, uncontaminated comparison** — both `0xC6444` and
`0x3AA96` are mode-proof, so V71C (gate live 0xFB, `0xC6444`=3072) vs V72 (gate dead 0xC5, `0xC6444`=512
stock) really is a dose-response, not an artifact of the mode bug. Causation not independently confirmed
here (needs the on-car measurement), but the bytes are reachable exactly as hypothesized.

## Mode 24 vs 26: 21 mode-indexed arrays diffed, struct-aware (true record length via each table's own
count field, not a fixed byte span) — [EVIDENCE, Python direct file read, `stock_fw_dump/code.bin`]
**19 of 21 byte-identical.** Two differ:
- `FUN_000348e0` array-C (`0xC95AC`, one of 5 angle-tracking blend arrays): Y0 376(mode24)→448(mode26)
  = **+19%**, plus ~1% shifts at 2 more Y points. Near the low end of an angle-tracking-error axis — the
  one plausible small engagement-conditional difference found this session. NOT yet tied to the prior
  "band0 (0-8km/h) flat zero" characterization in
  [[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]] — needs one more hop to
  confirm which of the two blended bands this array corresponds to.
- `FUN_000382d8` selector (`0xC7B40`): tail value 4181→4114 (−1.6%), minor.
- Identical: `FUN_00034350`'s FactorB/C/D/E/F, friction (`0xCBE74`), boost scalar (`0xCA324`), all 4
  r24/r26 arrays (destination bytes match even though the ADDRESSES differ), 4 of 5 `FUN_000348e0`
  arrays, `FUN_00035154`'s float LERP, `FUN_0003b338`/`FUN_0003b416`/`FUN_0003b49a`.

## Findings
- [EVIDENCE] Engagement re-points nearly every array to a physically different address, but the
  destination CONTENT is byte-identical for 19 of 21 — a relabeling, not a retuning, on this HW-ID
  variant (TVCA4). This is a clean negative result against "the mode switch retunes the assist chain."
- [BELIEF] The `0xC95AC` difference is too small (19% on one Y-point of a low-priority blend factor) to
  plausibly explain grind #1's engagement-conditionality by itself.

## Open questions
1. Which of `FUN_000348e0`'s 5 arrays (A-E) corresponds to "band0" vs "band1" in the creep-zero
   characterization — not resolved this session, would settle whether `0xC95AC`'s difference sits in the
   already-known-inert band or the live one.
2. `FUN_000382d8`'s downstream use of its tail value (`0xC7B40` offset 36).

## Related
[[reference_accord_gp63fd_full_enumeration_writers_and_13_reader_arrays]]
[[reference_accord_rate_lane_builds_were_never_single_variable]]
[[reference_accord_grind1_ladder_monotone_at_peak_velocity]]
