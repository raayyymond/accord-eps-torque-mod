---
name: reference_accord_gp67ac_resolved_zero_and_path1_always_live
description: gp-0x67ac (FUN_0003aa2c/Path-1 aggregator's wholesale-suppression gate) is CLOSED, always 0 at stock, by the identical mechanism that closed its twin gp-0x67ab -- Path 1's full 9-term direct sum (gp-0x6bd0 damper, gp-0x6bbe boost, gp-0x6b26 accel, gp-0x6ad4 PID, gp-0x6b86 peak-hold, gp-0x6ade, plus two clamped torque terms) is unconditionally live, never suppressed.
metadata:
  type: reference
---

# `gp-0x67ac` resolved zero -- Path 1's big sum is ALWAYS live, closing an open item

2026-08-11, `lane-weights-6bf` task (FUN_00038148 six-lane census for team-lead). Raw disasm of
`FUN_00026c80` (0x26c80-0x277fe, the 11-channel mixer) to settle whether `FUN_0003aa2c`'s (Path 1, the
aggregator that produces the delivered torque contribution) gate `if (reduce(gp-0x67ac)==1) { suppress
most terms }` is ever actually taken at stock.

## [EVIDENCE, raw disasm] `gp-0x67ac`'s producer traced to r22, computed identically to gp-0x67ab's r11

Both `gp-0x67ac` (`gp-0x3d98` source, write @`0x2773a`) and `gp-0x67ab` (`gp-0x3d94` source, write
@`0x2775c`) are populated inside the SAME 11-lane classification loop (`0x271de-0x27304`), from two
parallel accumulator paths (r22 for `67ac`, r11 for `67ab`) that both test `mode[lane] ∈ {2,3,4}` against
the per-channel mode array `tp+0x5124..0x512E = 0xC4124..0xC412E`. That array is **already established
in this kit's record as `[0,0,5,0,5,5,0,0,0,5,0]` — never 2, 3, or 4, for any of the 11 lanes**
(`reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction.md`, cross-validated independently
against `build_v41_tva.py`'s own quote of the same array).

Both accumulator paths (r22 @`0x27284`, r11 @`0x272ce`) share the identical branch shape: when
`mode[lane]` is never in `{2,3,4}`, the `cmp r0,r12(mode==4); be <label>` branch is ALWAYS taken and
lands on a fixed `r12=0` / `r10=0` value every iteration, regardless of lane, regardless of the
`gp-0x617c`/`gp-0x6170` RAM flag arrays that would otherwise gate it (those reads are structurally
unreachable given this mode array). `r27`/`r25` (the "sticky" carry flags) therefore never go nonzero
either, so the deterministic-zero result holds through all 11 lanes, not just the first.

⇒ **`gp-0x67ac` = 0 unconditionally at stock**, by the exact same mechanism as `gp-0x67ab`
([[reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction]]'s "gp-0x67ab — CLOSED, always 0
at stock" section, now extended to its twin).

## What this settles: Path 1's full sum is always live

`FUN_0003aa2c` (0x3aa2c, fresh decompile this session): `if ((byte)(reduce(gp-0x67ac))=='\x01')` gates
between a suppressed form (only `gp-0x6ade`, `gp-0x6b62`-derived terms survive, further zeroed by two
byte cals `tp+0x74ac`/`tp+0x74ab`) and the FULL form:
```c
iVar19 = iVar9(gp-0x6ade, ±1024 gate) + iVar19(gp-0x6b4c LKAS, ±10240 gate)
       + gp-0x6ad4(PID output, ±10240 gate) + iVar14(gp-0x6b62, ±8192 gate)
       + gp-0x6b26(±1024 gate) + gp-0x6bbe(±2048 gate) + gp-0x6bd0(±2048 gate)
       + gp-0x6b86(±12288 gate) + iVar21(torque-scaled, ±8192) + iVar16(torque-scaled, ±8192)
iVar14 += FUN_00036682()   // gp-0x6b46's OWN producer called a second time, here, unweighted
```
Since `gp-0x67ac==0` always, `reduce(0)=0*(0<2)=0 != 1` ⇒ **the ELSE branch (the full sum above) is what
actually runs, every cycle, at stock.** `gp-0x6bd0` and `gp-0x6bbe` (the damper and boost lanes) are
summed here **unweighted (plain ADD, no cal multiply)** — this is Path 1, the direct delivery path,
distinct from and additional to their weighted appearance in Path 2 (`FUN_00038148`'s `0xC63A0`/`0xC63A2`,
see [[reference_accord_gp6bd0_full_reader_enumeration_and_dual_path]] /
[[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]]).

## Related
[[reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction]] — the twin gate this extends.
[[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]] — Path 2's own structure,
which this file's Path-1 finding complements (both paths carry gp-0x6bd0/gp-0x6bbe, unweighted in Path 1,
weighted in Path 2).
