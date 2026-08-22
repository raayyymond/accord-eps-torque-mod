---
name: reference_accord_v850_ldw_stw_lsb_encoding_and_fun36c12_pcode_liveness
description: "V850 disp16 gp-relative encoding fully derived+validated from ground truth: hw1=(reg2<<11)|(opcode<<5)|reg1, hw2=raw displacement EXCEPT its LSB is an h-vs-w size discriminator on opcode 0x39/0x3B (0=h, 1=w/hu) -- a naive scan for st.w/ld.w MISSES every hit without this. Register-indirect scan method (movhi -0x121,r0,rN then positive low16-offset search under any base!=gp cross-referenced to a nearby movhi) fully implemented and run clean. Plus: real pcode liveness (get_function_pcode + hand-verified CFG) for FUN_00036c12's two V106 hook candidates."
metadata:
  type: reference
---

# V850 ld.w/st.w LSB encoding trap + full pcode liveness for FUN_00036c12's V106 hook candidates

2026-08-22, `tq-lowpass` subagent, GATE-1 follow-up (pcode sweep + raw byte census) for the V106 cave.

## 🛑 NEW TRAP: ld.w/st.w (and presumably ld.hu) use the SAME opcode as ld.h/st.h, disambiguated by hw2's LSB

Confirmed disp16 Format VII rule [EVIDENCE, ground-truth-validated against 3+ independent known examples]:
`hw1 = (reg2<<11) | (opcode<<5) | reg1`, `hw2 = displacement's raw 16-bit two's-complement value`,
opcode ∈ {0x38 ld.b, 0x39 ld.h/ld.w/ld.hu, 0x3A st.b, 0x3B st.h/st.w}.

**BUT**: a plain `hw2 = disp & 0xFFFF` search MISSES every `st.w`/`ld.w` access. Ground truth:
`st.w r11,-0x6d08[gp]` = bytes `64 5f f9 92` → hw2=0x92F9, while `disp=-0x6d08` as raw 16-bit two's
complement is 0x92F8 (LSB=0) — off by exactly 1. **The LSB of hw2 is a size discriminator on opcode
0x39/0x3B: 0 = halfword (ld.h/st.h), 1 = word-or-ld.hu.** Since every gp-relative RAM cell offset in
this firmware is even (2- or 4-byte aligned), the real displacement is always `hw2 & 0xFFFE`, and a
correct scanner must try BOTH `disp & 0xFFFE` and `(disp & 0xFFFE)|1` as candidate hw2 patterns. A scan
that only tries the raw disp value will silently return **0 hits for every word-accessed cell** and look
exactly like "nothing touches this address" — cost this session a false "0 hits" on all 5 of a prior
session's own pre-vetted candidate cells (`gp-0x6d08/6d04/6d00/6de8/6de4`) until caught and fixed.

## Register-indirect scan, fully worked method [EVIDENCE]

`movhi -0x121,r0,rN` encoding (ground-truth-validated against V90's own `0x55b1c` example, bytes
`40 96 df fe`): `hw1=(reg2<<11)|(0x32<<5)|reg1`, reg1=0, reg2=rN, hw2=0xFEDF (fixed). Scanning
`code.bin` whole-image finds **667 such sites** (any rN) — this pattern is common throughout the
firmware, not just at the one V90 found.

Key insight for finding register-indirect accesses to a SPECIFIC cell: after `movhi -0x121,r0,rN` sets
rN=0xFEDF0000, a subsequent `ld.h/st.h/ld.w/st.w offset[rN],rM` uses the **identical Format VII
encoding** already derived above, just with reg1=rN (not 4=gp) and a **POSITIVE** low-16 offset
(target_abs - 0xFEDF0000) instead of a negative gp-relative one. So: scan for the target's positive
low-16 offset under ANY reg1 != 4, then cross-reference each hit against whether a `movhi -0x121,r0,reg1`
occurs within a preceding locality window (300B used here) on the SAME register — a hit with no such
movhi nearby is very likely a coincidental byte match, not a real access (confirmed this session: 2 raw
candidates for `gp-0x4cd0` at `0xb9aea`/`0xb9cee` sat inside an ASCII string table — `"...KFC_EAT_158_
SNA\0KFC_ENG_13X_SNA..."` — not code at all, `get_function_by_address` returns nothing there).

## GATE-1 census, 3 methods, 8 cells — clean

`gp-0x6c2c` (8 disp16 hits), `gp-0x6b26` (5), `gp-0x4cd0` (2, the shadow pair, nothing else touches it),
`gp-0x6d08`/`6d04`/`6d00`/`6de8`/`6de4` (1 each, all `st.w`, exact address/register match to
[[reference-accord-gate1-write-only-diag-taps-are-the-best-cave-ram]] — REPRODUCED independently this
session, not stale). **0 six-byte extended-displacement hits, 0 genuine register-indirect hits, for
every one of the 8 cells.** Full detail (which functions read `gp-0x6c2c`/`gp-0x6b26`, addresses) in
[[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]] — this file is the METHOD record, that
one is the SUBJECT record.

## Real pcode liveness for `FUN_00036c12`'s two hook candidates [EVIDENCE, `get_function_pcode` + hand CFG]

Register-space offset map empirically confirmed: 0x00=r0, 0x0C=sp, 0x10=gp, 0x14=tp(!), 0x78=ep, 0x7C=lp,
else 4*N=rN.

**Hook B (`0x36cca`, post-scale/pre-clamp) — RESOLVED, cross-validated 2 ways** (full-function fixed
point AND an isolated sub-CFG starting at `0x36cca`, immune to any upstream loop-CFG error since nothing
downstream re-enters the earlier LERP-lookup loop): **live-out = {gp, tp, r6, r16} only.** r7/r8/r9/r10/
r11/r12/r13/r14/r15/ep/lp all confirmed dead. This is the recommended hook.

**Hook A (`0x36c1a`, the raw read) — r9 is definitively live** (CFG-independent: read again 3
instructions later at `0x36c26` on the sole straight-line path). Less useful as a scratch site.

🛑 **Unresolved residual**: the automated full-function sweep also shows `r12` live all the way back to
function entry — architecturally implausible (1-param function). Found+fixed FOUR real bugs in my
hand-built CFG for the internal LERP-table lookup loop (missing branch edges at `0x36c80`, `0x36c92`,
`0x36c6c`, `0x36c78`) and the anomaly persisted. Traced it to the pcode JSON showing **zero DEF at
`0x36c84`** despite the disassembly plainly reading `ld.h 0x4[r14],r12` there. **Not closed this
session** — either one more CFG edge is wrong, or Ghidra's high-pcode folds/relocates that op's effect
elsewhere in a way not yet tracked down. Does NOT affect Hook B (verified immune by construction).

Related: [[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]],
[[reference-accord-v90-cave-gate1-census-and-hook-critical-section]],
[[accord-gp4f60-two-encodings-enumeration-trap]]
