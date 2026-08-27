---
name: reference_accord_friction_lane_fun36c12_smooth_no_stickslip
description: FUN_00036c12 (gp-0x6b26 "friction comp" lane) fully decompiled+disassembled 2026-08-04 — it is a plain signed multiply of a speed-indexed magnitude LERP and gp-0x6c2c (motor-rate derivative), NO sign()/abs/hysteresis anywhere, smooth and continuous through zero. Corrects golden-model errors (gp-0x6c2e -> gp-0x6c2c; "AVG torque" axis -> voted vehicle speed gp-0x6a5e). Structurally CANNOT generate classical stick-slip. All its cals are virgin (zero build-script hits).
metadata:
  type: reference
---

**2026-08-04, team-lead mission "trace the friction lane for the grind #1 / micro-ratchet stick-slip
hypothesis."** Program: stock `code.bin` only (confirmed via `list_open_programs`, single program open).
Decompiled `FUN_00036c12` in full, then pinned the crux gate with `disassemble_function` (per
[[feedback-decompile-first-then-assembly]]).

## Verdict: NOT a stick-slip generator [EVIDENCE, decompile 0x36c12 + disasm 0x36c1a-0x36ce4]

`gp-0x6b26 = clamp( (gate(gp-0x6c2c) * sVar7 >> 6) * 0x111 >> 0x12, ±511 )`, `sVar7 = LERP(gp-0x6a5e, @0xCBE74[mode*4])`.

- `sVar7` (the magnitude table) is a standard 3-point piecewise-linear LERP — smooth, no discontinuity.
- `gate(gp-0x6c2c)` (disasm `0x36c1a-0x36c2c`: `addi 0x7d00,r9,r14` / `cmp 0xfa01,r14` / `cmovnc 0,r9,r13`)
  passes `gp-0x6c2c` through **unchanged** for the entire realistic range `[-32000, +32000]` and only
  zeroes it in the extreme negative tail `[-32768,-32001]` (768/65536 codes) — an **overflow/underflow
  guard**, not a near-zero or sign gate. Confirmed via raw instruction semantics (V850 `cmp Rm,Rn` = `Rn-Rm`;
  `cmovnc` = move-if-no-carry), not just the decompile's pointer-arithmetic rendering (which is a known
  Ghidra danger zone worth double-checking, per [[feedback-decompile-first-then-assembly]]).
- The final combine (`mulh r12,r13` / `sar 0x6,r13` / `mul r13,0x111,r0` / `sar 0x12,r6`, disasm
  `0x36cbe-0x36cca`) is a **plain signed multiply-and-scale**. No `abs()`, no `sign()` extraction, no
  hysteresis latch anywhere in the lane. **As `gp-0x6c2c` crosses zero, the lane's output crosses zero
  continuously and linearly** — structurally identical in kind to a viscous/rate-proportional damping
  term, not Coulomb friction. This rules the lane out as the discontinuity source for BOTH grind #1 and
  the micro-ratchet, cleanly and by direct evidence (not by absence of a positive finding).

## Corrections to golden-model / prior memory

1. **Input is `gp-0x6c2c`, not `gp-0x6c2e`.** `model/eps_lkas_chain_model.py` said `gp-0x6c2e`
   (fixed this session, both the summary table and the `assist_shaping_lanes` docstring). Disasm shows
   exactly one `ld.h -0x6c2c[gp]` in the whole function (`0x36c1a`); `gp-0x6c2e` never appears.
2. **LERP axis is `gp-0x6a5e` = voted VEHICLE SPEED, not "AVG torque."** Same correction already applied
   to FactorC/E in [[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]]; the golden model had
   fixed it for FactorC/E but left the friction-lane docstring stale (also fixed this session). Disasm
   confirms: `ld.h -0x6a5e[gp],r10` is the sole LERP index (`0x36c60`).
3. **Table re-confirmed by fresh byte read** (not just cited from memory): `0xCBE74[10*4]` -> `0xD2A44`,
   bytes `03 00 00 00 00 05 80 16 9a d9 9a e9 52 f8 00 00` = count=3, X=(0,1280,5760) [i.e. 0/20/90 km/h
   at 64 cts/km/h], Y=(-9830,-5734,-1966). **Magnitude is LARGEST at 0 km/h**, falling ~5x by 90 km/h —
   exactly the speed band where both symptoms occur, but see the phase caveat below before reading that
   as causal.

## Cal handles, all byte-read LE this session, program `code.bin`

| addr | tp/gp offset | value | role |
|---|---|---|---|
| `0xCBE74` | — | ptr array, mode*4 | table selector, mode10 -> `0xD2A44` |
| `0xD2A44` | — | count3, X(0,1280,5760), Y(-9830,-5734,-1966) | the magnitude LERP (mode 10 = this PN) |
| `0xC64FD` | tp+0x74fd | 5 | freshness sub-threshold on gate byte `gp-0x671a` |
| `0xC640A` | tp+0x740a | -8192 | flat fallback, `gp-0x671a` in [5,255) ("stale") |
| `0xC640C` | tp+0x740c | -3277 | flat fallback, `gp-0x671a`>=255 OR `gp-0x67f4`!=1 ("invalid") |
| `0xC407E` | tp+0x507e | 511 | self-clamp ceiling on the lane's own output, BEFORE the aggregator's own ±0x400(1024) gate |
| `0xC407C` | tp+0x507c | 461 | adjacent cal, NOT read by this function (only offset+2 is read) — unidentified owner |

**Lineage check [EVIDENCE, Python grep]: zero hits for `CBE74|D2A44|C64FD|C407E|C407C|C640A|C640C` across
every `build_v*_tva.py`.** This lane's cals have never been touched by any build in this kit's history —
fully virgin. (`0xC6B26` DOES appear in V43/V49 but is a different cal address entirely — "L1 Stage-A
gain Y row" 256/256/225/153 — not this RAM cell; do not confuse.)

## Gates `gp-0x671a` / `gp-0x67f4` — shared plausibility bytes, not engagement flags

Both are read by multiple other lanes (`gp-0x671a`: also `FUN_0003a382`'s continuous LERP index,
`FUN_000352b4`, `FUN_00035b20`, and the r24/r26 rate-lane index per
[[reference_accord_gp671a_blast_radius_not_a_free_lever]]; `gp-0x67f4`: the same "plausibility flag" that
also gates FactorC/D/E in `FUN_00034350`). Neither is LKAS-specific — consistent with the kit's
established fact that no cal-only LKAS fork exists for this class of lane
([[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]]).

## Task rate: confirmed 1 kHz [EVIDENCE, `get_function_callers`]

Sole caller of `FUN_00036c12` is `FUN_0002214a`, the kit's independently-confirmed 1 kHz control task.
No extra hold beyond `gp-0x6c2c`'s own producer cascade (fs_eff 312.5 Hz, per
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]]).

## Phase estimate — BELIEF, carried from the existing gp-0x6c2c cascade characterization, not independently re-derived this session

`gp-0x6c2c` vs `gp-0x4f50` (motor rate) is already characterized at 21 Hz: |H|=0.189 (-14.5dB), **+4.4°**
phase (per the lane-table memory above). This lane's own static LERP gain is a NEGATIVE real number
(`sVar7` is always negative) with no further phase contribution, so the lane's own phase vs `gp-0x4f50`
is ≈ **+4.4°+180° ≈ -175.6°** — close to the canonical -180° "opposes velocity" damping phase. **If this
holds, the lane is closer to a damping contributor than a destabilizer at 21 Hz** — a reason to be
CAUTIOUS about reducing it, not a reason to raise it. Flagged BELIEF because it assumes `gp-0x4f50`'s
phase relationship to the actual torque-sensor error carries through unchanged, which is the same
plant-dependent open question the aggregator-lane-table memory already flags.

## Resonance (gp-0x6ad4/FUN_0003a382) and magnitude (gp-0x6b86/FUN_000352b4) — brief pass, not re-traced fresh

Both smooth/continuous by existing structure (resonance is a genuine linear P/I/D on a clamped error term,
no sign() anywhere; magnitude is a peak-hold/envelope-follower, asymmetric attack/decay but not a
zero-crossing sign flip) — neither is a stick-slip candidate either, by the SAME reasoning as friction,
though this was not independently re-disassembled this session (inherited from
[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]] and
[[reference_accord_fun352b4_peakhold_correction_and_fun3a382_stageA_pole]]).

🛑 **Correction to an older agent-memory file**: [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]]
says resonance was "ELIMINATED V56" — that described the FLASHED-AND-LATER-REVERTED `0xC6AF0` mute.
Per `docs/BUILD-LINEAGE.md`/`docs/STATE.md`, V56 was falsified and reverted (V57+ carry the assertion
"0xC6AF0 must stay STOCK"), and the car is on V70/V71/V72 lineage now — **the resonance lane is LIVE on
the current build**, just structurally small at creep/ratchet speeds (164-341 counts, per a
speed-indexed ceiling LERP `0xC67C2`/`0xC67C8` starting at zero). Don't cite "eliminated" going forward.

## Related
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] — source of the gp-0x6c2c cascade phase
figures this file's phase estimate depends on; also the source of the stale "resonance eliminated" claim
this file corrects.
[[reference_accord_damping_friction_returncentre_torque_gates]] — first byte-dump of the same LERP table,
independently reproduced exactly this session (fresh read matches to the byte).
[[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]] — source of the gp-0x6a5e=voted-speed
correction this file also applies to the friction lane's own axis label.
