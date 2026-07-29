---
name: reference_accord_gp6806_phase_flag_and_dead_writer_split
description: "gp-0x6806 (the enable condition for FUN_00028ea6's 0x2a1ae-0x2a206 deadband+sign-relay block) is NOT an independent flag -- it is exactly `1 if phase(gp-0x679f) in {1,2,3,4} else 0`, where gp-0x679f is a phase byte of the SAME inline debounce/hold FSM already established as the live twin of dead FUN_0002a30e. Of 16 raw writer addresses found by a byte scan, only 8 (all inside FUN_00028ea6) are live -- the other 8 sit in the ALREADY-established dead/unclaimed gap [0x2a507,0x2a93a) and were re-confirmed dead this session by 2 independent null checks. Power-on/reset value NOT resolved -- traced the reset vector into what looks like BOOTLOADER init (0x8000-0x8bce, inside the kit's own BL=0-0xFFFF range) and found the bss-clear descriptor starting at the right RAM address (0xFEDF0000) is degenerate/skips unconditionally (covers 0 bytes) in this build; did not locate the APPLICATION's own crt0."
metadata:
  type: reference
---

# gp-0x6806 phase-flag identity + dead-writer split — traced 2026-07-29 for team-lead's build-decision question

Dispatched because team-lead's own byte scan found 16 raw `st.b` writers to `gp-0x6806` (disp16=`0x97FA`)
and needed: (1) power-on value, (2) reachability during normal engaged driving, (3) whether a self-latch
in the deadband block's `prev==0` clause could itself be the 20-25Hz driver. Full disasm of
`FUN_00028ea6` around `0x29380-0x29734` (the dispatcher containing 8 of the 16 addresses), plus
`get_function_by_address`/`get_function_callers`/`get_xrefs_to` checks on the other 8.

## [VERIFIED, 2 independent null-checks] 8 of the 16 writers are DEAD CODE

Team-lead's 4 "elsewhere" zero-writers (`0x2A80A/0x2A842/0x2A862/0x2A87E`) and the 4 "live-value" writers
`0x2A582/0x2A5B6/0x2A658/0x2A73C` **all fall inside `[0x2a507,0x2a93a)`** — the unclaimed gap this kit
already established as dead code (right after `FUN_0002a30e`, ends `0x2a507`; see
[[reference_accord_c646c_gain_feedback_vs_forward_classification]]'s `0x2a904` dead-code entry, same gap).
Re-verified `FUN_0002a30e` itself this session: `get_function_callers(0x2a30e)` → "No callers found";
`get_xrefs_to(0x2a30e)` → "No references found" (2 methods, both null, on the fully-analyzed `code.bin`).
`get_function_by_address` on `0x2a582`/`0x2a73c` both return "No function found" — consistent with the
same unbounded blob. **Only the 8 writers inside `FUN_00028ea6` are live.**

## [VERIFIED, disassembly, 8/8 addresses] gp-0x6806 = f(phase byte gp-0x679f), exact rule

```python
# gp-0x679f (phase byte, part of the inline debounce/hold FSM, live twin of dead FUN_0002a30e)
PHASE_TO_6806 = {
    0: 0,   # mode(gp-0x3d38)=1, written 0x2971e-0x29724 (full reset: ALSO zeros gp-0x69b0=AUTHORITY)
    1: 1,   # mode=3, written 0x2939c-0x293a6
    2: 1,   # mode=6, written 0x293ee-0x293e4
    3: 1,   # mode=2, written 0x29486-0x2948c (ALSO snaps gp-0x69b0 AUTHORITY to 0x8000 = full Q15)
    4: 1,   # mode=7, written 0x29588-0x2958c (ALSO snaps gp-0x69b0 AUTHORITY to 0x8000 = full Q15)
    5: 0,   # mode=4, written 0x29702-0x2970e
    6: 0,   # mode=8, written 0x2968a-0x29696
    7: 0,   # mode=5, written 0x296c8-0x296d2
}
gp_6806 = lambda phase: 1 if phase in (1,2,3,4) else 0
```
`gp-0x3d38` (a "mode" byte, values 1-8) is a DIFFERENT variable than `gp-0x679f`, stored alongside it at
every transition — not previously named in kit memory under this address; its relationship (if any) to
CAN `STEER_STATUS` is NOT established this session, flagged open.

**Reading**: phases 1-4 look like an ordinal ramp/confirm sequence (phases 3 and 4 both coincide with
`gp-0x69b0` AUTHORITY being snapped to full-scale `0x8000` — a wind-up-complete event); phases 0/5/6/7
look like idle/settled/reset states (phase 0 additionally zeros AUTHORITY entirely — a full reset).
`gp-0x6806==1` reads as "FSM mid-ramp"; `gp-0x6806==0` reads as "FSM idle or settled."

## [NOT RESOLVED] Power-on/reset value

Reset vector `0x0`→`jr 0x8000`. Traced CPU/PSW/gp/tp/sp setup `0x8008-0x812e` (confirms `gp=0xFEDF8000`
exactly via `movhi 0xFEDF0000` + `add 0x8000` — clean sanity check). This whole `0x8000-0x8bce` sequence
sits inside `[0,0xFFFF]`, this kit's own established BOOTLOADER range
([[reference_tva_accord_bootloader_map]]), and includes flash-CRC/magic-constant checks (`0xbb55`/`0xe718`/
`0xbdaa`/`0xb720`/`0xa900`) reading like bootloader integrity checks, not app crt0. Found a bss-clear-loop
skeleton starting at exactly `ep=0xFEDF0000` (`0x8a86-0x8ad8`, right neighborhood for `gp-0x6806`=
`0xFEDF17FA`) — **but its own bounds check (`cmp r8,r10 ; bnc SKIP` with `r8=0xFEDEC812 < r10=0xFEDF0004`)
causes it to skip unconditionally: this specific clear-descriptor covers ZERO bytes in this build.**
Did NOT locate the application's own entry/crt0 (as opposed to the bootloader's) in the time available.
`read_memory(0xFEDF17FA)` correctly fails ("Unable to read bytes") — it's live RAM, not in the flash
image, exactly as expected; this does not resolve the question. **Flagged open, not guessed at.**

## [PARTIAL] Reachability / self-latch reframed

The deadband+sign-relay block at `0x2a1ae-0x2a206` in `FUN_00028ea6` only RUNS when `gp-0x6806==0`
(phase∈{0,5,6,7}). Whenever the FSM transitions to phase 1 (mode 3), the WHOLE block — including its own
internal `prev==0` latch clause on `gp-0x6b30` — is bypassed wholesale, and `iVar34` passes through
unmodified. **The "healing" mechanism is gp-0x6806 itself flipping to 1 on the next phase transition, not
a property of the relay's own internal state.** Whether this happens on a 20-25Hz-compatible cadence is
NOT resolved — did not trace what gates each phase-to-phase transition (surrounding dispatcher compares
`gp-0x6803/6805/6807` against literals and `gp-0x69b0` AUTHORITY against LERP-derived bounds via
overflow-style `bnc`/`bgt` tests, not fully walked to concrete thresholds this session). One ANALOGY
(not a direct measurement): [[reference_accord_steerstatus4_dwell_constant_D]] records a 100-cycle
(~100ms) dwell elsewhere in this SAME FSM family's mode=4 handling — if phase transitions in general are
on a similar ~100ms scale, a clean 20-25Hz (40-50ms period) self-toggle is hard to reconcile, but this is
inference from a related-but-distinct dwell, not a measurement of `gp-0x679f`'s own cadence.

## Related
[[reference_accord_c646c_gain_feedback_vs_forward_classification]] — source of the `0x2a904` dead-code
precedent this session's writer-split reuses.
[[reference_accord_steerstatus4_dwell_constant_D]] — source of the ~100-cycle dwell analogy.
[[reference_tva_accord_bootloader_map]] — the BL=0-0xFFFF range this session's boot-trace falls inside.
