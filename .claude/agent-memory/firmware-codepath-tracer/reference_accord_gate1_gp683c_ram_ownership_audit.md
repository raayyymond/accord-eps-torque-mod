---
name: reference_accord_gate1_gp683c_ram_ownership_audit
description: "GATE-1 RAM-ownership audit of gp-0x683c (0xFEDF17C4) as a code-cave persistent-state byte. Seven access classes checked; all clear except a named residual. Key results: 1 reader / 0 writers confirmed by Ghidra AND a footprint-aware Python scan; NO constructed pointer anywhere in the image lands within 1.5KB; the three ep constants at 0xFEDF17C0/C1 all feed one sst.b at disp 0; the stack tops out 7,848 B below it; it is .data with boot initializer 0x00 from flash 0x86874; V67 verified to repoint its sole reader. ALSO records the inverted heuristic: in this binary a LONG free displacement run is evidence of a pointer-accessed ARRAY, not free RAM (69% of the gp window scans as free; the 2nd-longest run is a literal 0x0004-repeating table)."
metadata:
  type: reference
---

# GATE-1 audit: gp-0x683c as cave state — 2026-08-02

Target `gp-0x683c` = **`0xFEDF17C4`**. Program: stock `code.bin`.

## The seven access classes, and how each was closed [EVIDENCE]

| # | class | method | result |
|---|---|---|---|
|1|gp-rel disp16, all 6 opcode families, **footprint-aware**|Python full-image decode|**1** access covers the byte: `0x3AA94 ld.bu`. **0** writes|
|2|gp-rel disp23 extended|Python (hw2[10:4]+hw3 formula)|0 covering the byte|
|3|Ghidra's own view|`search_instructions operand_pattern=683c`|2 hits: the real read + `be 0x000683c2` @`0x683B2` text collision ⇒ **1 reader, 0 writers**|
|4|constructed pointers (`mov imm32`, `movhi`+`movea`)|Python resolve of all 712 `movhi 0xFEDF/0xFEE0` + all `mov imm32`|**nothing in `0xFEDF11B1..0xFEDF17BF` or `0xFEDF17C2..0xFEDF18C9`** — a ±1.5 KB pointer-free zone|
|5|LE32 pointer-table literals|`data.count()` for 0xFEDF17C2/C3/C4|**0** each|
|6|`ep`-relative `sld`/`sst`|Python ep-constant enumeration + Ghidra disasm|only 3 ep constants reach the page — `0xFEDF17C0` @`0x4CD12`/`0x4CD34`, `0xFEDF17C1` @`0x4CD26` — and **all three fall into one `sst.b r6,0x0,ep` @`0x4CD3C` (disp 0)**|
|7|stack|`sp` derivation @`0x140D8`|`sp = 0xFEDEF91C`, grows down ⇒ target is **7,848 B above** the stack top, unreachable|

**Boot writes DO exist** (see [[reference_accord_app_ram_layout_and_boot_init_loops]]): the cell is in
`.data`, zero-cleared then written from **flash `0x86874`**, whose value is **`0x00`** (confirmed twice —
Python read and Ghidra `read_memory 0x86860`, byte-identical). That positively explains the "dead gate":
the flag's writer was compiled out, the declaration and its single reader survived, default 0.

**V67 verified against `_v67_plain_image.bin`:** `0x3AA94` `847fc597` → `847ffb97`; decoded
`op=0x3C, bit5=0, disp=(0x97FB&0xFFFE)|0 = -0x6806` ⇒ `ld.bu -0x6806[gp],r15`. So on V67 the cell has
**zero gp-relative accesses of any kind**, and V67 leaves the `.data` source block untouched.

## The favourable asymmetry — worth stating on every cave review
V48B's brick was **cave writes → firmware reads → firmware misbehaves**. Here that direction is closed by
construction: the *only* firmware reader is `0x3AA94`, and V67 already points it elsewhere. The residual
runs the *other* way — firmware writes → cave's state glitches — which degrades our own logic, not the
motor command. **Not the same severity class.** (On **stock**, the direction is NOT closed: `0x3AA94` is
live and writing this byte would flip `FUN_0003aa2c`'s r24/r26 gain arm to cal `0xC6446`/`0xC6444`.)

## 🛑 Inverted heuristic — a LONG free run is a RED flag in this binary
"A byte in the middle of a long unaccessed run is safer" is **false here**. 16,970 of 24,577
displacements in `gp-0x7000..gp-0x1000` (69%) scan as unaccessed, because most RAM is
buffers/arrays reached by register-indirect pointers. Concrete proof: the **2nd-longest** free run
(1,307 B, `gp-0x61CF..gp-0x5CB5`) has a `.data` initializer of `04 00 04 00 04 00 …` — an unmistakable
repeating 16-bit table. Longest run (1,744 B) has 22 sparse nonzero initializers.

**Use the inverse ordering:** prefer a *short* hole (1–3 B) in a *dense* neighbourhood of individually
gp-addressed scalar flags, because there the allocator's behaviour is observable. Two extra
discriminators this audit produced:
- **Section**: `.data` (`gp-0x6E50..gp-0x2598`) vs bss — `.data` means a declared object with a designed
  initial value.
- **Initializer**: a free byte whose flash initializer is **nonzero** (e.g. `gp-0x682B`/`gp-0x682A` = 0x01,
  `gp-0x6823` = 0xFF) is *worse* — something was meant to read it. Prefer initializer `0x00`.

## Neighbourhood note
`gp-0x6850..gp-0x6820` is a **dense scalar-flag block**: 42 of 49 bytes individually accessed by
gp-relative byte ops from ~30 different functions (`FUN_00052cce`/`FUN_00052e32`/`FUN_00053216`,
`FUN_0004c780`, plus the 0x3Cxxx–0x3Fxxx cluster). Topologically the same shape as the
`gp-0x1401..gp-0x1502` region the kit calls POISON — but the specific V48B failure mode (a 16-bit cell
whose *high byte* aliased a packed flag) does not apply to a **1-byte** request audited with a
**footprint-aware** scan. The free holes in that block are `gp-0x683C, 0x6831, 0x682B, 0x682A, 0x6828,
0x6826, 0x6823`.

## What was NOT ruled out
A base pointer **loaded from RAM/flash at runtime** plus a computed index, and **DMA**. Neither leaves a
constant in the image, so neither is statically excludable; both are bounded only by the absence of any
constant, literal, or gp-relative reference to this address anywhere in 1 MB. Also unproven: that no
transitive callee of `FUN_00046f20` inherits the live `ep=0xFEDF17C0` across `0x4CC94 jarl`
(`FUN_00046f20` itself is clear — its decompilation declares `unaff_gp`/`unaff_tp` but **no `unaff_ep`**).

## Related
[[reference_accord_app_ram_layout_and_boot_init_loops]] · [[reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule]] · [[reference_v850e2_extended_disp23_encoding_solved]]
