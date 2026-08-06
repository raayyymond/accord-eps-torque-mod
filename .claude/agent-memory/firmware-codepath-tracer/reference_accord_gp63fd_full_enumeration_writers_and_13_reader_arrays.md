---
name: reference_accord_gp63fd_full_enumeration_writers_and_13_reader_arrays
description: Full enumeration of gp+0x63fd (mode selector byte) — 3 writers (boot populator + engagement re-selector + UDS WDBI) and 13 mode-indexed reader arrays across 11 functions, cross-validated by independent Python byte scan. Closes the open "never boot-populated" question and explains V73's on-car {8,10} engagement-linked measurement.
metadata:
  type: reference
---

**Entry point & goal**: enumerate every consumer of `gp+0x63fd` (positive gp-relative offset, absolute
`0xFEDFE3FD`), the per-mode assist-curve selector, after V73's probe measured it live over 104,061 CAN
frames taking exactly two values {8,10}, switching on every LKAS engagement edge (1.02s rise / 2.08s
fall, 18/18 transitions, 99.09% lag-matched to `latActive`). [EVIDENCE throughout unless noted.]

## Method + coverage (all 4 methods agree)
`search_instructions operand=63fd`: 31 hits, 3 are false positives (branch targets in `FUN_00063ee8`
whose target address contains "63fd" as a substring, not gp-relative accesses) → 28 real. Independent
Python LE byte scan (disp16 per-opcode formula + disp23 formula from
[[v850e2-extended-disp23-encoding-solved]]): 27 disp16 + 1 disp23 = 28 — **exact match, no undercount**.
LE32 literal scan for absolute addr `0xFEDFE3FD` found **1 more**: register-indirect UDS read (`mov
0xfedfe3fd,r6` @`0x4a982`, `FUN_0004a8ca`) invisible to gp-relative scans. **Total 29 accesses, 14
functions.**

## Writers (3, all fully traced)
1. **`FUN_00042692`** (1 write, `0x426ae`) — **boot-time populator**, gated `gp-0x6d78 & 8 != 0`. Calls
   `FUN_00057f8e` (HW-ID row match, the team-lead's pointer-chase recipe) and copies row-column
   `tp+0xE012`. **Closes the previously-OPEN question in
   [[reference_accord_config_key_gp6408_udsonly_writer_bss_no_boot_populator]]** — that memory's sibling
   cell `gp+0x6408` may still lack a populator, but `gp+0x63fd` itself does not; whether this boot path is
   reachable depends on `gp-0x6d78` bit3, not independently verified this session.
2. **`FUN_00042746`** (4 writes, `0x4279e/0x427c4/0x427fc/0x42822`) — **the engagement re-selector**.
   Picks one of 4 HW-ID-row columns (`tp+0xE012/13/14/15`) keyed on two 2-state flags `gp-0x67f6`/
   `gp-0x67e2`, whose own transitions are driven by `gp-0x6806` (==`latActive` at 99.983% per
   [[reference_accord_gp6806_phase_flag_and_dead_writer_split]]) and `gp-0x69b0` (engagement gate,
   [[reference_accord_gp69b0_authority_gate_and_fun42746_table_selector]] already named this function)
   crossing sentinels `-0x8000`/`0`. [EVIDENCE, fresh decompile 0x42746-0x347b4] This is the mechanism
   behind V73's {8,10} engagement-linked measurement — prior label "sensor-fault failover reselector"
   (in `eps_lkas_chain_model.py`, now corrected) undersold it: it fires on engagement edges, with
   `gp-0x67e2`'s branch additionally gated on a consistency check vs cal `tp+0x7182`.
3. **`FUN_0004a798`** (1 write, disp23 6-byte form, `0x4a7fc`) — UDS WDBI dispatcher, request-ID case 1
   (`r8==1`). Same dispatcher also writes `gp+0x63e8/0x6426/0x6427/0x63ec/0x63f0/0x63f4/0x6400/0x6404` —
   same config cluster as `gp+0x6408`. Bench-only, no CAN RX path.
Plus non-torque-path: UDS RDBI reader (`FUN_0004a8ca` @`0x4a982`) and diagnostics packer
(`FUN_000508e8`, 2 reads, copies the raw byte value — not as an index — into a telemetry buffer).

## Readers — 13 distinct mode-indexed pointer arrays, 11 functions
Previously known (2): `FUN_00034350`'s 5 damping factors (see
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]]), `FUN_00036c12` friction
(`0xCBE74`).
Also known but not previously tied to this byte explicitly: `FUN_0003ad74` r24/r26 speed-blend (3
pointer arrays + `tp+0xd214`, breakpoints 0/10/50/100km/h at `tp+0x7010`=`0xC6010`).
**NEW this session (7 arrays, 6 functions):**
- `FUN_00034a72` (boost, gp-0x6bbe) — `PTR_DAT_000ca324[mode]`, single scalar cal (not a LERP).
- `FUN_000348e0` — 5 sub-arrays (`PTR_DAT_000c92f4`/`PTR_LAB_000c93dc`/`PTR_LAB_000c95ac`/`DAT_000c94c4`/
  `DAT_000c9694`), already characterized in
  [[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]] as the gp-0x6a10
  angle-tracking blend, flat-zero at creep band.
- `FUN_00035154` — `PTR_DAT_000c7888[mode]`, float LERP indexed by speed `gp-0x6a62*0.015625`(km/h).
- `FUN_000382d8` — `LAB_000cc9fc[mode]` + `PTR_DAT_000c7b40[mode]`, speed `gp-0x6a64`-keyed selector,
  structurally similar to `FUN_0003ad74`'s speed-band selector.
- `FUN_0003b338` — `PTR_DAT_000c8198[mode]`, standard LERP struct, index var not resolved.
- `FUN_0003b416` — `DAT_000ca5dc[mode]`, indexed by `gp-0x6a5e` (voted speed), gated `gp-0x67f4==1`.
- `FUN_0003b49a` — `DAT_000cbca4[mode]`, feeds `gp-0x6b28`; index var not resolved.

## Findings
- [EVIDENCE] Engagement re-indexes damping, friction, boost, and both rate lanes simultaneously — a wide
  structural reach, not a footnote.
- [EVIDENCE] Mode 8's FactorC X0=1280ct=20km/h; mode 10's X0=2240ct=35km/h (team-lead's own byte reads,
  matching my prior mode0/mode10 reads exactly). **8km/h (512ct) is below both** ⇒ the "damping
  architecturally zero at 8km/h" conclusion in
  [[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] is UNCHANGED by which
  mode is live.
- [BELIEF, not shown] Whether the 7 new arrays differ meaningfully between mode 8 and mode 10 at low
  speed is untested — the most promising next step to connect this byte to the 8km/h symptom.

## Open questions / verification needed
1. `FUN_0003b338`/`FUN_0003b416`/`FUN_0003b49a`'s full index-variable derivations and downstream
   consumers — addresses only, roles not resolved.
2. Diff each of the 13 arrays' mode-8 vs mode-10 records specifically (not just FactorC).
3. `get_function_callers` on `FUN_00022ca0` (the boot-populator's caller) returned an empty/null result —
   not cross-checked with a Python xref scan; treat as unresolved, not a verified zero.

## Related
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]]
[[reference_accord_config_key_gp6408_udsonly_writer_bss_no_boot_populator]]
[[reference_accord_mode_selector_fun42746_closed_confined_to_10_11]] — SUPERSEDED further: this file
confirms `FUN_00042746` is real and engagement-linked, but the "confined to {10,11}" range claim is
WRONG per V73's fresh telemetry ({8,10}, not {10,11}).
[[v850e2-extended-disp23-encoding-solved]]
