---
name: reference_accord_v36_gentle_eme_debounce_full_mechanism
description: Full byte-verified mechanism of the V36-blanked STEER_STATUS debounce SM (0xC61C0/C2/C4 + 0xC64B4-B8) — exact reader addresses in both FUN_00028ea6 and FUN_0002a30e, and why it is NOT the ratchet/grinding cause
metadata:
  type: reference
---

**Task**: `blanked` subagent, 2026-08-27, for `team-lead`/`main`. Fresh GhidraMCP re-verification (prior
record was r2-era, 2026-07-14) of the three cells named-but-unexplained in
`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md:62`: `0xC61C0`/`C61C2`/`C61C4` (1600/896/1280 stock), blanked to
`0xFFFF` at V36, still `0xFFFF` through **V110** (current tip as of 2026-08-27; byte-confirmed on stock +
V107/V108/V109/V110 `_plain_image.bin`). Companion torque cals `0xC64B4/B5/B6/B7`=112/96/64/54→**0xFF**×4
(also V36) and `0xC64B8`=112→**0xFF** (V37, the separate DTC-0x49 counter fix) confirmed 0xFF in the same 4
builds. Run is exactly 6 bytes, `0xC61C0`-`0xC61C5`. Adjacent `0xC61BE` (LKAS request clip,
[[reference_accord... c61be]] elsewhere) = 15360 byte-stock in all 4 — genuinely separate cell, no overlap.

**EVIDENCE — exactly 12 reads, 0 writers**, matching the historical "12 readers" figure exactly, now with
addresses (Ghidra `disassemble_bytes` dry_run, cross-validated against a raw Python LE byte scan; ⚠
`get_bulk_xrefs` gave the known false "no references found" on all three — 5th recorded instance of that
trap in this session-family):

| cell | `FUN_00028ea6` rise | `FUN_00028ea6` hold | `FUN_0002a30e` rise | `FUN_0002a30e` hold |
|---|---|---|---|---|
| `0xC61C0` | `0x2924a` | `0x292c4` | `0x2a42c` | `0x2a4a6` |
| `0xC61C2` | `0x2925e` | `0x292d8` | `0x2a440` | `0x2a4ba` |
| `0xC61C4` | `0x2926e` | `0x292e8` | `0x2a450` | `0x2a4ca` |

All `ld.hu <disp>,tp,rN`. Both functions implement the **identical 4-tier OR-envelope** (decompile of
`FUN_0002a30e` + disassembly of the `FUN_00028ea6` twin, both fresh this session):
```
torque(gp-0x682f) > 0xC64B4(112,rise)/0xC64B5(96,hold)   OR
rate(param_1)      > 0xC61C0(1600)                        OR
(torque > 0xC64B7(64)  AND rate > 0xC61C2(896))           OR
(torque > 0xC64B6(54)  AND rate > 0xC61C4(1280))
```
Trips after 5 consecutive qualifying cycles (`0xC64E2`=**5**, byte-confirmed — ⚠ read as **1 byte** `char`,
not u16: a u16 read here gives a wrong 5125) → `gp-0x6807`(STEER_STATUS)=4, reseed via `0xC64DF`=**100**
(also 1 byte). The trip site itself (`0x29276`-`0x2929a`, `0x2a458`-`0x2a47c`, both fully disassembled)
writes ONLY `gp-0x6807=4`, `gp-0x6758=0` (resets the separate DTC-0x49 counter B), `gp-0x6757`=reseed — no
torque/current/PWM/damping/rate-limit register anywhere in the trip's local block.

**Adjudicated false positives** from the raw scan (per `firmware-decompile` skill's instruction-boundary
warning, confirmed via `disassemble_bytes`): `0x38eca` and `0x47ed0` are the tail halves of unrelated 2-byte
`shl`/`add` register ops (bytes `c1 71` coincidentally matching `disp16|1`), not loads. `0xc44f0` is outside
any function (`get_function_by_address` → "No function found"), not part of the reader set.

**Own-tooling gotcha, recorded so it doesn't recur**: my first raw-Python pass silently missed all 4
`0xC61C4` hits — a bug in MY scan (`data.find(patt, pos, region_end)` starting `pos=0`; if the pattern's
first hit anywhere in the file is *before* `region_start`, my `if idx < region_start: break` aborted the
whole search instead of skipping forward). Not a firmware fact, a scripting bug — caught only by
cross-checking against Ghidra's disassembly. Always advance `pos = max(idx+1, region_start)` on a
pre-region hit, don't break.

**Relevance to the operator's live symptoms (grinding 15-40mph, ratcheting at high LKAS demand, max-rate
cap) — NOT the cause of any of them, reasoned:**
1. Level-threshold + 5-cycle debounce, not periodic — cannot produce an in-band oscillation by construction.
2. Signals watched (`gp-0x682f` arbitrated torque; `param_1` an unnamed rate magnitude, `FUN_0002a30e` has
   **0 static callers** — called indirectly, caller still UNRESOLVED as of this session, same open item as
   2026-07-14) are structurally different from the ratchet's well-characterized 7.79 Hz `gp-0x6b26`/
   `gp-0x6c2c` inertia-derivative path (see the shared kit's `reference_accord_ratchet_*` family).
3. Max steering rate is a different cell entirely (`0xC61BE`, confirmed byte-stock through V110 in this
   same session — see [[reference_accord_gp6807_gates_gp69b0_engagement_ramp]]).

**Verdict**: this is the intended, on-car-confirmed (V37, flashed 2026-07-14) gentle-EME fix, correctly
still in force. Not a lever for anything currently being chased. See
[[reference_accord_gp6807_gates_gp69b0_engagement_ramp]] for a genuinely new correction to the historical
"STEER_STATUS=4 is report-only" framing — the fix itself is still sound, but STEER_STATUS's *reach* is
larger than the 2026-07-14 record found.
