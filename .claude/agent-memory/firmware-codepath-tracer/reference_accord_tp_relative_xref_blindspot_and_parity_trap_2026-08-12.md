---
name: reference_accord_tp_relative_xref_blindspot_and_parity_trap_2026-08-12
description: Two GhidraMCP/scan traps hit and confirmed during the 0xC63A6 GATE trace -- get_xrefs_to returns a false "No references found" on tp-relative displacements (must be overridden by search_instructions + a raw byte scan, never trusted alone), and a bit0-in-hw2 parity trap where a scan keyed on one hw2 value silently addresses the neighbour cal cell one byte over.
metadata:
  type: reference
---

# Two confirmed tool traps, `c63a6-gate-trace` session, 2026-08-12

## Trap 1: `get_xrefs_to` returns a FALSE ZERO on tp-relative displacements

`get_xrefs_to(0xC63A6)` on `code.bin` returned **`"No references found to address: 0xc63a6"`** --
despite `0xC63A6` having a real, live reader (`ld.hu 0x73a6,tp,r15 @0x381ca` in `FUN_00038148`,
confirmed by decompile, `search_instructions`, AND a raw Python LE byte scan). This is the SAME class
of blind spot already on record for this kit (`firmware-decompile` skill: "a recorded case of Ghidra's
xref engine returning a misleading zero on a tp-relative displacement") -- this session is a second,
independently-confirmed instance, on a different address.

**Rule, reconfirmed**: `get_xrefs_to` on a `tp`-relative cal address is NOT trustworthy as a null result
by itself. Any "nothing reads this" claim built on `tp`-relative addressing must be corroborated by
`search_instructions(operand_pattern=<hex disp>)` **and** a raw Python LE byte scan (both bit0 parities
-- see Trap 2) before it is reported as EVIDENCE. `get_xrefs_to` remains useful as a POSITIVE signal
(if it finds something, that's real) but its negative signal on `tp`-relative addresses is not reliable.

## Trap 2: the `ld.hu`/`ld.h` bit0-in-hw2 parity trap addresses the NEIGHBOUR cell

Confirmed on `0xC63A6` this session: the real instruction's hw2 field reads **`0x73a7`** (not `0x73a6`)
-- Ghidra decodes the displacement as `0x73a6` because bit 0 of hw2 is NOT part of the displacement for
this instruction class, it's fixed at 1. A raw byte scan that keys ONLY on the bare displacement value
(`0x73a6`) as a 16-bit LE pattern finds **zero hits** even though the real instruction is right there --
you must scan for `disp | 1` as well (`0x73a7`), or decode the field properly.

**A second, independently-reported instance from a teammate this session** (relayed, not verified by
me directly): a scan on `0xC64B8` with hw2 = `0x74B9` actually addressed **`0xC64B9`, the neighbour
byte**, because the opcode field selects between `0x3C` (even displacement, bit0=0 in the field) and
`0x3D` (odd displacement, bit0=1 in the field) -- the SAME underlying trap the shared kit memory
`accord/firmware/accord-v850-scan-traps-formatv-and-storezero.md` documents for `ld.bu`, now confirmed to also bite
`ld.hu` in at least one instance, and worth treating as general to the halfword-load family, not just
byte loads, until proven otherwise.

**Rule**: any raw byte scan for a `tp`- or `gp`-relative cal address must check BOTH `disp` and `disp|1`
as the hw2 pattern, and any hit must have its DECODED displacement (not just the raw hw2 bytes) checked
against the target address before being counted -- a raw-byte match one bit off can silently point at
the wrong cell entirely, over- or under-reporting readers/writers.

## Why this matters beyond this one trace

Both traps independently produce FALSE NEGATIVES or MIS-ATTRIBUTED HITS on exactly the address-class
(`tp`/`gp`-relative cal reads) that this kit's GATE-1/GATE-2 census work depends on most heavily. Every
"N readers, M writers" claim in this domain should be treated as provisional until both `search_instructions`
and a raw byte scan (both parities) agree, per the kit's standing tool policy -- this session is two more
data points for why that policy exists, not two new exceptions to work around.

## Related
[[reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split]] -- the trace this session's traps
were caught during.
`docs/guides/FIRMWARE-DECOMPILE-GUIDE.md`, `.claude/skills/firmware-decompile.md` -- the standing trap list this
extends (shared, not owned by this agent-memory).
