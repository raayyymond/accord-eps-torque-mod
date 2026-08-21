---
name: reference_v850_search_instructions_base_register_collision_trap
description: search_instructions' operand_pattern matches on the displacement TEXT only, not the base register -- a scan for "0x3814" returns both real gp-0x3814 hits AND unrelated tp-0x3814 hits (a completely different physical address, tp-0x3814=0xBB7EC vs gp-0x3814=0xFEDF47EC), inflating a raw hit count and requiring manual per-hit base-register adjudication before any GATE-1 "sole accessor" claim.
metadata:
  type: reference
---

Found 2026-08-20, `self-interference-cancellation` design task, while GATE-1-verifying
`gp-0x3814`/`gp-0x3818` (Honda's dead biquad state cells) as RAM candidates for a new cave filter.

## The trap [EVIDENCE]

`search_instructions(operand_pattern="0x3814")` on stock `code.bin` returned **6 matches**, but only
**2** are the cell of interest:

```
00035a4c FUN_000352b4  ld.w -0x3814, gp, r16     <- REAL: gp-0x3814 = 0xFEDF47EC
00035a64 FUN_000352b4  st.w r11, -0x3814, gp     <- REAL: gp-0x3814
000837e6 FUN_000837c0  ld.w -0x3814, tp, r13     <- FALSE POSITIVE: tp-0x3814 = 0xBB7EC (different cell!)
00083c6c FUN_00083b9e  ld.w -0x3814, tp, r26     <- FALSE POSITIVE
0008562e FUN_00085284  ld.w -0x3814, tp, r24     <- FALSE POSITIVE
00085a28 FUN_000857d2  ld.w -0x3814, tp, r20     <- FALSE POSITIVE
```

`tp = 0xBF000` and `gp = 0xFEDF8000` are entirely different base registers pointing at entirely
different physical regions (flash-anchored cal/const data vs the gp-relative RAM window). The tool's
`operand_pattern` is a substring match against the rendered operand STRING (`"-0x3814, gp, r16"` vs
`"-0x3814, tp, r13"`), so a bare displacement-value query like `"0x3814"` matches BOTH bases whenever
they happen to share the same numeric offset -- which is common, since both `gp` and `tp` offsets are
small positive integers drawn from similar ranges. **A raw match count is therefore not usable for a
GATE-1 "how many accessors" claim without manually reading each hit's base register field.**

By contrast, the sibling query `"0x3818"` returned exactly 2 hits, both `gp`-relative, both inside
`FUN_000352b4` -- no collision that time, purely because no `tp-0x3818` cal cell happens to be
dereferenced anywhere in this image. **The absence of a collision on one displacement is not evidence
the method is safe in general** -- it is safe only for THAT specific displacement value, by chance.

## How to apply

- **Always inspect the base-register field of every `search_instructions` hit** before using a raw
  match count as a GATE-1 "N accessors" number, especially for RAM-candidate cells (`gp`-relative) where
  a `tp`-relative false positive at the same numeric displacement is easy to miss at a skim.
- This is a DIFFERENT trap from the already-documented "gp/tp-relative accesses have TWO encodings
  (disp16 vs 6-byte extended)" and "`ld.bu` displacement parity" traps in
  `.claude/skills/firmware-decompile.md` -- it is specifically about `operand_pattern` text-matching
  being base-register-blind, not about an encoding form being invisible to the scan. Worth folding into
  that skill file's trap list if a maintenance pass touches it.
- Cheap mitigation: query with the base register included in a follow-up mental filter (the tool has no
  base-register parameter to query on directly), or cross-check suspicious hits with `get_assembly_context`
  (as done this session) to see the full rendered instruction before trusting the count.

## Related
[[reference_accord_fun352b4_full_chain_gp6b82_tap_and_c6200_shared_clamp]] -- the session this was found
in, and the GATE-1 result (clean: 2 real `gp-0x3814` hits, 2 real `gp-0x3818` hits, all inside
`FUN_000352b4`'s gated biquad block) once the false positives were excluded.
