---
name: accord-can-frame-330-deadbits-wholeimage-confirmed
description: 2020 Accord TVA-A160 (V850E2, master.bin) — whole-image (185,116-instruction) confirmation that CAN 0x14A/330 byte4 bits7:3 (gp-0x1514/0xFEDF6AEC) and byte7 bits7:6 (gp-0x1511/0xFEDF6AEF) are never written by ANY instruction anywhere in the program, not just within builder FUN_00055a98. Closes the open item in [[reference-accord-can-tx-frame-0x14a-bytemap]].
metadata:
  type: reference
---

# Whole-image dead-bit confirmation: CAN 330 (0x14A) byte4[7:3] / byte7[7:6]

Session 2026-07-13, read-only Ghidra MCP audit on `program="master.bin"` (stock code.bin, 2113 fns,
185,116 total instructions per `search_instructions` scan count). Builds on
[[reference-accord-can-tx-frame-0x14a-bytemap]], which left an explicit open item: "run a whole-image
grep for the literal displacements -0x1514/-0x1511 against gp to rule out a stray writer" before using
these bits as a live piggyback.

## Method
`search_instructions` (operand substring, program-wide, no function filter) for:
- `-0x1514` (byte4 gp-relative disp) and `-0x1511` (byte7 gp-relative disp) — exact anchor forms.
- `1514` / `1511` broad substrings — to catch anything the anchored form might miss (also picks up
  false positives from jump-target addresses that happen to contain those digits; each was individually
  vetted and excluded, see below).
- `6aec` / `6aef` — absolute-address low-16 forms (for the `movhi -0x121,r0,rX; clr1/set1/tst1 N,0x6aec,rX`
  idiom used elsewhere in this same builder for the fault-path bit clears).
- `fedf6aec` / `fedf6aef` — full absolute literal, in case Ghidra renders a symbol/full-address form.
- `jarl` callers of `FUN_0002193e` (the one non-`FUN_00055a98` function that also touches gp-0x1514).

## Results

**gp-0x1514 (byte4, absolute 0xFEDF6AEC):** exactly 10 real hits program-wide, ALL inside
`FUN_00055a98` (6: `ld.bu`/`st.b` pairs at `0x55aac/0x55ac0`, `0x55ad4/0x55ae8`, `0x55af4/0x55b06` —
bits 2, 1, 0 respectively, confirmed via direct disassembly of `0x55aa0-0x55b3f`: masks `andi 0xfb`,
`0xfd`, `0xfe`) or its ONE private helper `FUN_0002193e` (2: `ld.w`/`st.w` at `0x2194a`/`0x21964`).
`FUN_0002193e` has **exactly 1 static caller in the whole image** (`0x55b44`, inside `FUN_00055a98`
itself — confirmed via `jarl` operand-pattern search for its entry `0x0002193e`). Its store is a
32-bit masked RMW with a **hardcoded literal mask `0xff0000ff`** (`mov 0xff0000ff, r15` at `0x21954`,
not parameter-derived) that preserves ALL 8 bits of byte4 and byte7 while replacing bytes 5/6 — i.e.
even this helper structurally cannot touch byte4 bits regardless of caller.

Two absolute-form `clr1` instructions also confirmed (`0x55b1c-0x55b34`, fault path): `movhi -0x121,r0,r18`
(r18=0xFEDF0000) then `clr1 1,0x6aec,r18` / `clr1 0,0x6aec,r18` — bits 1 and 0 only, matching the normal
path exactly. Zero absolute-form hits for bits 2-7 anywhere (the `6aec` search only returns these same 2
instructions plus 2 unrelated false positives at a completely different displacement, see below).

**Zero hits** for `fedf6aec` (full absolute form) anywhere in the program.

**gp-0x1511 (byte7, absolute 0xFEDF6AEF):** exactly 4 real hits program-wide, ALL inside
`FUN_00055a98` (`0x55bf2/0x55c02` bits 5:4 rolling counter; `0x55c1c/0x55c2a` bits 3:0 checksum nibble).
**Zero** absolute-form hits (`6aef` and `fedf6aef` both return 0 matches) — i.e. byte7 has no absolute-addressed
bit-instruction anywhere, unlike byte4's fault-path bits 0/1.

## False positives excluded (documented so a future session doesn't re-flag these)
- `search_instructions` operand substring matching is naive text-match, not semantic. Two classes of
  false positive were hit and individually verified as unrelated:
  1. Branch/jarl **target addresses** that happen to contain the digit substring (e.g. `br 0x00015148`
     contains "1514"; `jarl 0x0003c4e2` contains "c4e") — these are absolute PC targets, not gp-relative
     displacements, and were excluded by confirming the full target address does not fall in the
     addresses of interest.
  2. **Unrelated displacements/bases** that coincidentally share digits: `ld.h -0x6b00,gp,r8` inside
     `s_motor_torque_rate_shaper` (0x431a0 etc.) matched a "6b00" search but is displacement **-0x6B00**
     (absolute 0xFEDF1500), nothing to do with absolute address 0xFEDF6B00 — a completely different RAM
     location reached via a completely different (and much larger) gp offset. Always re-derive
     `gp + displacement` by hand before trusting a hex-substring hit.

## Verdict
**CONFIRMED, whole-image, not just builder-scoped:** byte4 bits7:3 (mask 0xF8) and byte7 bits7:6
(mask 0xC0) of CAN frame 0x14A (330) are dead — never read, written, set, or cleared by any instruction
anywhere in `master.bin`. Safe to treat as a piggyback target from a code-cave-based extension, subject to
the standard caveat that a fully register-indirect/computed-offset write (base pointer loaded far from
this literal, then indexed at runtime) cannot be excluded by static literal-scan alone — no such pattern
was observed for this specific location (contrast with the mailbox-descriptor array in
[[reference_accord_free_ram_candidates_gp1500_gp14e0]], where that risk IS live for nearby addresses).
