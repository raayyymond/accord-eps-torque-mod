---
name: reference_accord_mode_selector_fun42746_closed_confined_to_10_11
description: CLOSES the mode-selector lead F7 flagged and could not follow. FUN_00042746's gp+0x63fd mode byte is engagement-linked (VERIFIED via branch conditions on gp-0x6806/gp-0x69b0) but the single ROM table at 0xCD000, row "TVAA1", has mode candidates [10,10,11,11] -- PHASE alone determines mode in {10,11} for this vehicle, SELECTOR is irrelevant. V72 edited both 10 and 11 to nearly-identical values, so the mode flip is real but does NOT explain the gp-0x6bd0/damper null. Also identifies the 3rd writer FUN_00042692 and the UDS-diagnostic writer FUN_000508e8.
metadata:
  type: reference
---

# Mode selector FUN_00042746 fully decoded — 2026-08-05

Dispatched by team-lead after finding the `0xD30`/gp-0x67fa work (see
[[reference_accord_task5_100hz_live_verified_full_producer_census]]) and flagging that F7 had already
found `FUN_00042746` writes `gp+0x63fd` (the mode byte every FactorB/C/D/E table in `FUN_00034350`,
`FUN_00034a72`, `FUN_00036c12`, `FUN_0003ad74` etc. reads) but had not followed it further.

## [EVIDENCE] The complete writer census, live `get_xrefs_to(0x63fd)`, 7 writes total

- `FUN_00042746` (4 writes, `0x4279e/0x427c4/0x427fc/0x42822`) — sole caller `FUN_00022ca0` = task5/100Hz.
- `FUN_00042692` (1 write, `0x426ae`) — reachable from task1/1kHz under state gate `{1,3}`, but its ENTIRE
  body is gated `if ((gp-0x6d78 & 8) != 0)`. `gp-0x6d78`'s sole writer image-wide (`search_instructions`,
  16 hits, 1 real write) is `FUN_000197b8`, a generic `word |= 1<<bit` setter with **no clearing anywhere**
  — bits are one-way/sticky (consistent with this kit's existing "gp-0x6d78 bit15 ONE-WAY" finding).
  Which event sets bit 3 specifically is [OPEN], not resolved this session — but doesn't matter: this
  writer reads the SAME `e012` table field via the SAME `FUN_00057f8e()` lookup, so it can only ever
  write the SAME value `FUN_00042746`'s PHASE=0 branch would — no new mode value introduced.
- `FUN_000508e8` (2 writes) — see below, a UDS-diagnostic routine, not part of the periodic cycle.

## [EVIDENCE] `FUN_00042746`'s state machine, fresh decompile + disasm this session

Two independent axes select one of 4 ROM-table fields:
- **PHASE** (`gp-0x67f6`, 0/1/other) transitions via explicit tail-of-function branches: PHASE→0 needs
  `gp-0x6806==0` AND `gp-0x69b0==0` AND `gp-0x4f68 < cal(tp+0x7180)`. PHASE→1 needs `gp-0x6806!=0` AND
  `gp-0x69b0==0x8000`(signed `-0x8000`) AND the same threshold AND `gp-0x6804==0`.
- **SELECTOR** (`gp-0x67e2`, tracks `gp-0x6733`) updates on `gp-0x6733 != current && gp-0x6733 != -1 &&
  gp-0x4f68 < cal(tp+0x7182) && !debounce_pending`.
- Both feed `FUN_00057f8e()`: a 5-byte ASCII-key exact-match search (16-row linear scan, returns 0 on no
  match) against RAM `gp+0x6408-640c`, picking a row in **one ROM table at `0xCD000`**, 16 rows x 36 bytes.
  Row layout: bytes 0-4 = ASCII key, byte 0x12/0x13/0x14/0x15 = the 4 mode candidates (PHASE x SELECTOR),
  byte 0x17/0x18 = 2 auxiliary values (written to `gp-0x674f`).

## [EVIDENCE, fresh byte read] The `0xCD000` table content — the decisive finding

Full 576-byte read this session. Every row's key is an ASCII part-number-style string. **Row 2 = "TVAA1"**
(matches `docs/BUILD-LINEAGE.md`'s documented PN->key mapping for `39990-TVA-A160` — [BELIEF: not
independently re-verified against a live read of `gp+0x6408-640c` this session, inherited from that doc).
**Row 2's 4 mode candidates: `e012=10, e013=10, e014=11, e015=11`.** SELECTOR is irrelevant for this row —
mode is a PURE function of PHASE: **PHASE=0 -> mode 10, PHASE=1 -> mode 11.** Only these two values are
ever reachable for this vehicle. (Not a general table property: e.g. row 8 "TVAA7" has all 4 candidates
distinct — `[12,13,14,15]` — so other vehicle identities WOULD see a real 4-way mode split; TVAA1 happens
to collapse to 2.)

Full table (key: e012,e013,e014,e015 / aux e017,e018):
```
00000:0,1,2,3/0,1        TVAA0:4,4,5,5/2,2      TVAA1:10,10,11,11/5,5  TVAC1:10,10,11,11/5,5
TVAA2:4,4,5,5/2,2        TVAA4:4,4,5,5/2,2      TVAA6:10,10,11,11/5,5  TVAC4:10,10,11,11/5,5
TVAA7:12,13,14,15/6,7    TVCA0:16,16,17,17/8,8  TVCA3:22,22,23,23/11,11 TVCA4:24,25,26,27/12,13
TVCA6:22,22,23,23/11,11  TWAA0:28,28,29,29/14,14 TWAA1:28,28,29,29/14,14 TWAA2:30,31,32,33/15,16
```

## [EVIDENCE] Mode IS engagement-linked, verified from the branch conditions themselves

Per this kit's prior characterization (inherited, not re-derived fresh): `gp-0x6806` is "99.98%
correlated w/ LKAS engaged" ([[reference_accord_gp69b0_authority_gate_and_fun42746_table_selector]]) and
`gp-0x69b0` is the LKAS engage-ramp AUTHORITY (Q15, 0..0x8000). The branch conditions above require
EXACTLY `gp-0x6806==0`+ramp-retracted for PHASE=0 and `gp-0x6806!=0`+ramp-full for PHASE=1 — so **mode
genuinely flips 10 (disengaged, ramp retracted) <-> 11 (engaged, ramp fully authorized)**, confirmed from
the code, not inferred. Ordinary engaged creep driving (LKAS engaged, authority ramp at full) runs
**mode 11**.

## [EVIDENCE] But this does NOT explain the gp-0x6bd0/damper null — V72 already covers both

V72's FactorC edit: mode10 Y=`[430,430,430,877]`, mode11 Y=`[431,431,431,877]` — differ by exactly 1 count
in Y[0]/Y[1], a rounding-level difference, functionally identical. **Whichever mode the engagement state
selects, V72's fix is equally in force.** The mode-flip mechanism is real, now fully decoded, but is NOT
the cause of the recorded gp-0x6bd0/bit4 null (0/87,940 frames per team-lead) — that must be explained
elsewhere (the seed/FactorA thread, per [[reference_accord_gp6bd0_seed_ruled_out_and_engagement_gates_found]]).

## `FUN_000508e8` — the UDS-diagnostic writer, NOT part of the driving cycle

A UDS-shaped routine (sub-function byte 0=read/report current config, 1=write-new-key with NRC 0x31
rejection if `FUN_00057f8e()` finds no match) that can read AND REPROGRAM the hardware config key
`gp+0x6408-640c` itself (also flash-backed default load from `0x14500`, and CAN/session reinit on a
successful change). No RTOS/task caller found — reached via UDS RoutineControl/WriteDataByIdentifier
dispatch, i.e. factory/service programming, not the periodic 1kHz/100Hz cycle.

## 🛑🛑 MAJOR FOLLOW-UP (2026-08-05, same day): see [[reference_accord_config_key_gp6408_udsonly_writer_bss_no_boot_populator]]
The "TVAA1 = row 2, live mode is 10/11" conclusion below is now CONDITIONAL, not settled. Traced
`gp+0x6408-640C`'s writer exhaustively (5 independent methods): the ONLY writer image-wide is a UDS
RoutineControl/WriteDataByIdentifier handler taking bytes from an external request payload — NOT from any
ROM ID string, and the cell is confirmed `.bss` (zero at boot, no `.data`-copy restoration). **If nothing
else populates it, this vehicle's live mode may actually resolve to row 0's fallback `[0,1,2,3]`, never
10/11, on ANY build including stock** — a search for an alternate boot-time computed-pointer populator
(the one blind-spot class not yet ruled out) was not completed. Read that file before treating "mode is
10/11" as closed.

## Open items
- Which event sets `gp-0x6d78` bit 3 (gating `FUN_00042692`) — not resolved, doesn't change the verdict.
- `gp+0x6408-640c`'s live runtime value not independently read this session — "TVAA1"/row 2 rests on
  `BUILD-LINEAGE.md`'s documented mapping, not a fresh on-car or byte-level confirmation. **UPGRADED to a
  major open question, see the follow-up above** — the mapping may not even be reachable at runtime.
- `FUN_00057f8e()`'s exact indexing edge case (returns 0 on no-match, which is ALSO row 0's valid index,
  key "00000") not stress-tested — a genuine no-match and a match-on-row-0 are indistinguishable from the
  return value alone; not load-bearing here since row 0 isn't a real vehicle identity anyway.

## Related
[[reference_accord_gp69b0_authority_gate_and_fun42746_table_selector]] — the earlier session (F7-adjacent)
that found this lead and flagged it unresolved; this file closes it.
[[reference_accord_gp6bd0_seed_ruled_out_and_engagement_gates_found]] — the seed/FactorA thread that is
now the remaining open explanation for the gp-0x6bd0 null, since this mode-selector thread is closed.
[[reference_accord_task5_100hz_live_verified_full_producer_census]] — source of the live task-rate methods
reused here (`get_xrefs_to`, `get_function_callers`, `search_instructions` cross-checks).
