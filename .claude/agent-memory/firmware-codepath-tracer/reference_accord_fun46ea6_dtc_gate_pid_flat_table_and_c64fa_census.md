---
name: reference_accord_fun46ea6_dtc_gate_pid_flat_table_and_c64fa_census
description: FUN_00046ea6(5) (the gate skipping gp-0x671a's whole reversal-FSM) tests bit5 of a DTC-confirmed-status OR-accumulator (gp-0x18d0|gp-0x18d4), reset at boot + by a monitor-readiness sweep, NOT a permanent block -- verdict (a) tuning starvation, moderate confidence. FUN_0003a382 (PID) reads gp-0x671a as a genuine LERP index into its OWN cal (0xC67B2, distinct from 0xC64FA) but that table's 3 Y-knots are ALL 1024 -- byte+disasm-confirmed unconditional no-op, resolves a previously-flagged uncertainty. NEW 4th consumer FUN_00035b20 (gp-0x671a<cal 0xC64FA=5) feeds gp-0x69a0, whose sole other touch is inside the dead-biquad function FUN_000352b4. 0xC64FA full census: 18 real touches across 5 functions (2 methods, cross-validated) -- reconciles build_v103's "~18 readers" claim -- INCLUDING 10 in FUN_00025c32 that search_instructions completely missed (a fresh instance of the documented undercount trap) and that look UNRELATED to the oscillation-detector family. Landmine confirmed, wider than previously recorded.
metadata:
  type: reference
---

# `gp-0x671a`'s skip-gate, the PID's dead table, and `0xC64FA`'s true blast radius — 2026-08-20, `docs/traces/TRACE-2026-08-20-oscillation-detector.md`

Full write-up: `docs/traces/TRACE-2026-08-20-oscillation-detector.md`. This file is the durable-fact summary.

## `FUN_00046ea6(5)` — bit 5 of a DTC-confirmed-status accumulator, NOT a permanent block

`FUN_00046ea6(uint bit)` returns bit `bit` of `(*(uint*)(gp-0x18d0) | *(uint*)(gp-0x18d4))` — disasm
(`0x46ea6-0x46eca`) confirms the decompile exactly (`ld.w` both halves, `or`, variable `shr`, `shr 0x1`,
`setfc`). `FUN_000428d4` calls it with `bit=5`; nonzero **skips the ENTIRE reversal-FSM including the
`st.b` write to `gp-0x671a`** for that tick.

`gp-0x18d0`/`gp-0x18d4` are **OR-accumulators, never overwritten, only OR'd** via `FUN_0001601e`/
`FUN_000160c8`, each with exactly 3 callers (`FUN_0001612c`, `FUN_000166d0`, `FUN_00016928`) — all three
are **DTC/monitor debounce state machines** (28-byte descriptor table at `tp-0x72C4`=`0xB7D3C`, 2-byte
RAM status words at `gp-0x18ce`, OBD-II-style status-byte literals `0x1603`/`0x2088`/`0x2098`/`0x20a8`/
`0x20b8` observed). Cleared to 0 **only** by `FUN_000178c6`, called from a one-time boot/HW-init routine
(`FUN_00057e5e` — also inits `gp-0x6752` polarity and the `gp-0x67fa` state gate) **and** from
`FUN_00047622`, itself invoked by a pending-retry poll (`FUN_0001702c`) or a repeatedly-run 8-slot
monitor-readiness consistency sweep (`FUN_00047f78`) — i.e. **re-evaluated more than once per drive
cycle**, not latched forever after boot.

**Bit 5's owner**: `read_memory` of 10 sampled descriptor entries at `0xB7D3C` found exactly ONE
(index 3, `0xB7D90`) with bit 5 set in its offset+8 mask (raw 45 = `0b101101`). **Exact DTC identity not
resolved** (no index→OBD-code table traced). **Verdict for the (a)/(b) starvation question: (a),
moderate confidence** — the gate is narrow (one DTC slot, not "any fault"), resets periodically, and
V67/V68's fault-free drive record makes a permanently-latched bit5 unlikely, though this is circumstantial,
not a direct read of the flag's live value.

## `FUN_0003a382` (the PID) — `gp-0x671a` reaches it as a LERP index into a table that is FLAT AT UNITY

Exact site `0x3a4a6: ld.bu -0x671a,gp,r14`, feeding a genuine continuous LERP (`BASE=0xC67B2`,
X=(10,15), Y=(`0xC67B8`=1024, `0xC67BA`=1024, `0xC67BC`=1024)) — **all three Y knots equal 1024**,
divided by 1024 (Q10) at the combine. **`gainD_raw`=1.000000 exactly for EVERY value of `gp-0x671a`
(0-255), independently of the `>=5` duty question entirely** — there's no threshold behavior to be
starved of; the table itself is dead. Byte-confirmed via `read_memory` AND disasm field-offset
cross-check (both agree). **Resolves the flagged uncertainty in
[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]]** ("gainD_raw ~1024/1024,
NOT independently re-verified") — now confirmed, not merely estimated. 🛑 `0xC67B2` is a **separate cal
cell** from `0xC64FA`, despite both currently holding 5 — do not conflate them.

## `FUN_00036c12` (friction) predicate confirmed unchanged from prior session's finding

`gp-0x671a < cal(0xC64FD)=5` selects the normal speed-LERP; `>=5` (and `<0xff`) selects flat fallback
`cal(0xC640A)=-8192`; `>=0xff` or `gp-0x67f4!=1` selects flat `cal(0xC640C)=-3277`. **Another separate
cal** (`0xC64FD`, not `0xC64FA`). Counter values 0-4 are computationally IDENTICAL (same branch, same
LERP) — nothing changes below 5. Matches this agent's own prior-session file
[[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]] / [[reference_accord_gp671a_creep_value_and_friction_lane_schedule]]
exactly — independently re-confirmed via fresh decompile this session.

## NEW: `FUN_00035b20` is a 4th `gp-0x671a` consumer, and it feeds the dead-biquad function directly

`bVar1 = gp-0x671a < cal(0xC64FA)=5` selects between two speed/rate-indexed ceiling schedules (axis
`gp-0x6a64`): **LERP_C** (`<5`, normal — `tp+0x7936`, Y=358/358/461/512 rising) vs **LERP_B** (`>=5` —
`tp+0x7912`, Y=358/307/307/307, flat-and-lower). Result is `min()`'d against a third LERP, rate-limited,
stored to `gp-0x69a0`. **`gp-0x69a0` has exactly 2 touches image-wide**: this write, and the sole read is
`0x352e2` **inside `FUN_000352b4` — the dead-biquad/notch function** — i.e. Honda's reversal counter
modulates a ceiling feeding directly into the SAME function as the notch, via a route separate from the
notch's own arm condition. Exact numeric role of `r18` inside `FUN_000352b4` not re-traced this session
(inherited "peak-hold output stage" characterization).

## `0xC64FA` full census — LANDMINE, wider than the existing record states

Two independent methods, cross-validated:
- Ghidra `search_instructions` on the CORRECT operand text `"74fa"` (not `"64fa"` — tp-relative operands
  render as the raw displacement, not the resolved address; an initial search on `"64fa"` returned only
  2 branch-target-text false positives — self-caught before reporting): **8 hits** — 5 self-reads inside
  the producer `FUN_000428d4`, 1 each in `FUN_000352b4` (biquad arm), `FUN_00035b20` (new), `FUN_0003aa2c`
  (r24/r26 arm).
- Raw Python LE scan, full 1 MiB image, both `ld.bu` parities: **21 raw candidates.** The same 8, plus
  **10 NEW hits at `0x260BC-0x261A2`, inside `FUN_00025c32`** (defined function, body
  `0x25c32-0x26c7f`) — **completely invisible to `search_instructions`** (fresh instance of the
  documented "scans only already-analysed instructions, `truncated:false` regardless" trap). Disasm
  (`disassemble_bytes dry_run:true`) confirms a genuine unrolled 4-sub-slot loop using CEIL as an
  increment/compare bound in what looks like an unrelated debounce/match-window counter — **no reference
  to `gp-0x671a` anywhere in that loop**. 3 raw hits excluded with stated reason: `0x7B2B6` disasm-proven
  to be mid-bytes of an unrelated `sst.w`; `0xBDB7B`/`0xBEEBB` have no defined function (data region).

**Total 18 real touches / 5 functions — reconciles exactly with `builds/v80_v107/build_v103_tva.py`'s "~18 in-code
readers" claim**, which this session's first (Ghidra-only, wrong-substring) pass could not confirm.
**Verdict: LANDMINE, confirmed independently and found WIDER than recorded** — `0xC64FA` gates 4
oscillation-response consumers AND is separately reused inside an apparently-unrelated subsystem
(`FUN_00025c32`, purpose not characterized this session). V103's precedent (private in-place repoint of
one consumer's arm SOURCE, e.g. `FUN_000352b4`→`gp-0x6806`) is the safe pattern if any of these are to be
armed; `FUN_00035b20`'s site (`0x35BE6`) is a named, unexplored candidate for the same treatment, not
byte-specified this session.

## Related
[[reference_accord_gp671a_shared_starved_gate_biquad_and_r24r26]] — prior session's starvation finding
and the V103 correction this file's Task 1 extends (adds the DTC-gate structure and the (a)-verdict).
[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]] — source of the flagged
gainD_raw uncertainty this file resolves.
[[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]], [[reference_accord_gp671a_creep_value_and_friction_lane_schedule]]
— prior full trace of `FUN_00036c12`, independently reconfirmed here.
[[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]],
[[reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short]] — source of the 42.3Hz
pole / 55.2Hz zero figures cited in this session's frequency-mismatch synthesis (not re-derived here).
