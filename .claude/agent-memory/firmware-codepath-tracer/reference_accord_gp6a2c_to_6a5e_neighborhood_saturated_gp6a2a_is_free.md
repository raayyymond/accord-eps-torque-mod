---
name: reference_accord_gp6a2c_to_6a5e_neighborhood_saturated_gp6a2a_is_free
description: The gp-relative RAM neighbourhood immediately around gp-0x6a32 (the V288 setpoint-filter state cell), swept gp-0x6a1a through gp-0x6a5e (23 halfword candidates), is almost entirely occupied by live shared state across many unrelated functions. gp-0x6a2a, gp-0x683c, gp-0x6ab0, gp-0x68b0, and gp-0x6c44 are confirmed free by a FULL raw byte-level census (every ld.b/ld.bu/ld.h/ld.hu/ld.w/st.b/st.h/st.w/6-byte-extended encoding, gp-based bit-ops, absolute-pointer literals, and movhi/movea register-indirect proximity, all zero) -- see docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md's two final addenda for the full method and an opcode-table correction (st.b is a clean single opcode 0x3A for both parities, NOT colliding with st.h/st.w -- an earlier hand-arithmetic error of mine said otherwise). gp-0x6ab0/gp-0x6aaa and gp-0x68b0/gp-0x68aa are each verified free 2-word (8-byte) runs; gp-0x6c44..gp-0x6c3a is a verified free 3-word (12-byte) run. A 4-word (16-byte) run verified to the same full standard was not found in the time available, though the systematic scan found 266 candidate runs (22,212 free bytes total) not yet individually verified for register-indirect risk.
metadata:
  type: reference
---

# `gp-0x6a2c`..`gp-0x6a5e` is saturated; `gp-0x6a2a` is the one clean free cell found near `gp-0x6a32`

🛑 **UPDATE, same session**: `search_instructions` alone (below) is NOT the final word — `main` correctly
required the CLAUDE.md-mandated raw Python byte scan as a second method. That full re-census (every
`ld.b`/`ld.bu`/`ld.h`/`ld.hu`/`ld.w`/`st.b`/`st.h`/`st.w`/6-byte-extended encoding, `gp`-based bit-ops,
absolute-pointer literals, `movhi`/`movea` proximity) RE-CONFIRMED `gp-0x6a2a` free and additionally
found `gp-0x683c`, `gp-0x6ab0`/`gp-0x6aaa` (a verified free 2-word run), `gp-0x68b0`/`gp-0x68aa` (another
2-word run), and `gp-0x6c44`..`gp-0x6c3a` (a verified free 3-word/12-byte run). One decode error of mine
(`st.b`'s opcode, a hand-arithmetic slip) was caught and corrected mid-census. Full method, the opcode
table, and the verdict are in `docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md`'s
two final addenda — read those before citing this file's ORIGINAL body below, which predates the fix.

2026-09-08, subagent `tracer`, stock `code.bin` (Ghidra `search_instructions`, whole-program scope,
operand-text matching on Ghidra's own resolved decode — immune to hand-rolled opcode-table bugs).
Produced while answering `team-lead`'s Q4 (RAM census for an in-loop biquad state, following up on the
V288 setpoint-filter cave which already claimed `gp-0x6a32`).

## The negative finding, and why it matters

Swept every halfword-aligned displacement `gp-0x6a1a` through `gp-0x6a5e` (23 candidates spanning the
V288 state cell's immediate ±0x30-byte neighbourhood). **21 of 23 are occupied** by real `ld.h`/`ld.hu`/
`st.h` gp-relative accesses, confirmed by Ghidra's own operand text showing `gp` as the base register
(not a false-positive digit collision). Several are touched by 6+ *unrelated* functions
(`FUN_00028ea6`, `FUN_0002a93a`, `FUN_000534da`, `FUN_0004e378`, `FUN_0002db94`, `FUN_00042376`, ...) —
this whole RAM region is a shared linker-pooled static-data block, not per-function-private, so
**adjacency to a known-free cell (`gp-0x6a32`) is NOT evidence the neighbour is also free.**
[[reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site]]

## The one clean cell

**`gp-0x6a2a` (0xFEDF15D6), halfword.** Zero gp-relative hits in a whole-program
`search_instructions operand_pattern:"6a2a"` sweep. The single raw text hit (`0x66a2a`, inside
`FUN_000669d6`) is a branch-target digit coincidence — base is a code address, not `gp` — the documented
`reference_accord_operand_text_search_false_positive_wrong_base_register` class. No `movea -0x6a2a,gp,...`
anywhere (checked explicitly, separate from the general sweep).

**Residual, not papered over**: register-indirect access via a `movea` of a nearby-but-different
displacement (e.g. `-0x6a20` or `-0x6a1c`, both of which DO have `movea` bases in `FUN_00041eec`)
walking forward to reach `0x6a2a` was not excluded. No evidence found for it; not proven impossible.
Also not checked: whether `0x6a2a` sits inside a crt0 block-clear range (would be benign if so).

## The other two candidates, and why a 4th was not found

- `gp-0x683c` (byte): re-confirmed dead-in-V282/V288 this session (the stock reference at `0x3AA94` is
  exactly the V104 rate-lane-gate instruction the build repoints via the `0x3AA96` byte edit
  `0xC5`→`0xFB`, converting `-0x683c` to `-0x6806`). See [[reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site]].
- `gp-0x6994` (halfword): 1 writer, 0 gp-relative readers — but an EXISTING documented residual
  (324 unbounded `mov imm32` RAM-base sites below it, block-copy reach not excluded). Not newly clean.
- Extended the sweep to the adjacent filter-state bank (`gp-0x3d28/2c/38/40`) — all four occupied by
  `FUN_00028ea6`/`FUN_0002b422`/`FUN_00023d24`'s own byte-granular state.

**No 4th fully clean cell was found by this method.** A biquad's full 4×32-bit state (8 halfwords) needs
a proper systematic full-image gp-relative occupancy map (every displacement 0x0000–0x7FFF, both 4-byte
and 6-byte extended forms), not more one-at-a-time `search_instructions` calls — flagged as the exact
next step, not run this session.

## Method note: `ld.bu`/`st.b` displacement recovery NOT re-derived

Attempting to independently re-derive the `ld.bu` displacement-recovery formula from `0x3AA70`
(`ld.bu -0x671a,gp,r12`, bytes `8467e798`) produced numbers inconsistent with a simple
`(hw2<<1)|opcode_bit0` model. Not chased further — not load-bearing for a halfword/word census, since
`search_instructions` operand text already resolves the true displacement regardless of the underlying
encoding trick (it parses AFTER Ghidra's SLEIGH decode). Byte-level (ld.bu/st.b) neighbours of the
"free" cells above are therefore an honest, un-certified residual, same discipline
`docs/specs/design/SPEC-V288-SETPOINT-FILTER-CAVE-2026-09-07.md` §2.3 used for its own byte-adjacent
candidate.

See full census: `docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md`.
