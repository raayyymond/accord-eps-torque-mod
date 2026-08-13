---
name: reference-accord-v98-gate1-four-cells-and-span-scanner
description: GATE 1 RAM-ownership enumeration for gp-0x6bfe / gp-0x6bfa / gp-0x6752 / gp-0x374c on the V97 image, plus the reusable span-overlap scanner that enumerates EVERY gp-relative access rather than keying on one displacement. Includes the 0x2A90A unanalysed-region reader and proof the flown cave's store set is exactly 2 cells.
metadata:
  type: reference
---

Done 2026-08-12 against `_v97_V96BASE-C63AC.102to150_plain_image.bin` and stock `code.bin`.
Scanner: `scratchpad/gate1_scan.py` (harness-validated on both images before use).

## The method that matters: enumerate, then filter by SPAN

Every previous scan in this kit keyed on **one exact displacement**. That is structurally blind to a
32-bit access at a *different* displacement whose 4-byte span covers the cell. The fix is to decode
**every** gp-relative load/store in `[0x13000,0x100000)` into `(disp, width, R/W)` and then filter
`disp < D+size and disp+width > D`. Same code answers the exact-hit question and the span question,
and it cannot be wrong about the span in a way the narrow scan is silent about.

Result for all four cells: **zero SPAN-only hits — every access is EXACT.** Nearest non-overlapping
writers (a useful sanity check that the filter is live, not stuck): `gp-0x374c` has `st.h -14158`
at `0x37822` (ends 2 bytes short) and `st.w -14152` at `0x396c8` (starts 4 bytes past);
`gp-0x6752` has `st.b -26452` at `0x42252` (2 short) and `st.b -26447` at `0x426c4` (3 past).

## Counts — report the two tools SEPARATELY

| cell | Ghidra `search_instructions` | Python scan | union | R / W |
|---|---|---|---|---|
| `gp-0x6bfe` | 2 | 2 | 2 | 1 / 1 |
| `gp-0x6bfa` | 5 | 5 | 5 | 2 / 3 |
| `gp-0x6752` | **55** | **56** | **56** | 51 / 5 |
| `gp-0x374c` | 2 (stock) | 2 stock / **4 V97** | 4 | 3 / 1 |

**`gp-0x6752` is the seventh reproduction of "Ghidra silently undercounts".** The Python-only hit is
`0x2A90A` = `0477ae98` = `ld.b -0x6752[gp],r14`. `get_function_by_address` returns *No function found*;
`find_code_gaps` puts it inside the gap **`0x2A508-0x2A939`** (1074 bytes, `has_undefined_bytes:true`,
between `FUN_0002a30e` and `FUN_0002a93a`). Linear decode through it is coherent —
`0x2A904 ld.h 0x746c[tp],r6` (a tp cal load; **this is the same idiom my memory already records as
missed at `0x2a904`**), `0x2A908 add imm5,r12`, `0x2A90A` our `ld.b`, `0x2A910 ld.hu 0x71b4[tp],r15`.
It is a READ, so it does not change any ownership verdict — but the *count* was wrong in the brief
either way. **The brief's "55 sites, 49R/6W" was wrong in both halves** while its five named writer
addresses were right, i.e. a hand miscount, not a tool disagreement.

## The four cells

- **`gp-0x6bfe`** (abs `0xFEDF1402`) — observer MODEL term. Sole writer `FUN_0003bc20` @`0x3bc3e`:
  reads `gp-0x6bfc`, and if `x + 20000u >= 0x9c41` (i.e. `|x| > 20000`) writes the **`0x7FFF` sentinel**
  and sets `gp-0x695c = 0xFFFF`, else passes `x` and sets `gp-0x695c = 0x400`. Confirms the gate-flag
  equivalence recorded in [[reference-accord-observer-gate-tautology-and-term-mismatch]].
- **`gp-0x6bfa`** (abs `0xFEDF1406`) — written only in `FUN_00026c80` (the assist-channel mixer) as a
  **±0x4E20 (±20000) clamp with a shadow copy at `gp-0x4cfa`**; every `st.h` to `gp-0x6bfa` is paired
  with an `st.h` to the shadow, and a mismatch branches to `movea -0x4cfa,gp,r6` → the shadow-fault
  handler. Same ±20000 envelope as `gp-0x6bfe`'s gate.
- **`gp-0x6752`** (abs `0xFEDF18AE`) — **boot-time table-parsed, shadow-validated static**, shadow at
  `gp-0x4c2d`, fault handler `FUN_0006b9fa`. `FUN_00048a40` is a TLV record parser: record type `0x54`
  sub `0x10` reads `psVar10[2]` and writes **`1` if `','`(0x2C), `0xFF`(-1) if `0xFA`**.
  `FUN_000490ac` is the init driver (calls `FUN_00048a40` up to 400× waiting on `gp-0x3488`).
  `FUN_000497e6` re-asserts the same value from the same table pointer `gp-0x34b8`.
  **Independently re-derives [[reference-accord-polarity-gp6752-static-boot-config]] by decompile.**
- **`gp-0x374c`** (abs `0xFEDF48B4`) — Stage-1 accumulator, read `0x381FE` / written `0x38230`, both in
  `FUN_00038148`. V97 adds two cave reads at `0xC4B40` and `0xC4B78`.

## The flown cave's store set, proved differentially

Diffing *all* gp-relative WRITES between V97 and stock (not just the cave region) returns **exactly 2**:
`0xC4B74 st.b r6,-0x1514[gp]` and `0xC4B9A st.b r6,-0x1511[gp]`. Nothing else in the image writes a
different cell than stock does. This is the cheap, complete way to audit "the cave stores to nothing
new" — far stronger than reading the cave listing, because it also catches an accidental edit elsewhere.

## Side-effect and alignment clearance (reusable)

- The **datasheet-authored SVD** `UPD70F3508_V850E2Px4.svd` has **58 peripheral `baseAddress` entries,
  all in `0x40000000-0x407EC000`, none in `0xFEDF0000-0xFEDFFFFF`.** ⇒ the whole gp page is internal
  RAM and **a load there is side-effect-free**. Cite this instead of asserting "it's RAM".
- Ghidra's memory map is a single flat block `ram: 00000000-000fffff` = the flash image only. There is
  **no block at `0xFEDF____`**, so `get_xrefs_to` / `list_globals` / `audit_global` can never answer a
  gp-cell ownership question on this program. That is a tool limitation, **not** a zero.
- Alignment (computed, not eyeballed): `0xFEDF1402`/`0xFEDF1406` halfword-aligned, `0xFEDF48B4`
  word-aligned (`0x48B4 % 4 == 0`), `0xFEDF18AE` byte. All naturally aligned.

## Address-synthesis / register-indirect closure

Three probes over `[0x13000,0x100000)`, all on the V97 image:
- **A** literal 32-bit LE words equal to `addr-3 .. addr+size-1` (catches `mov imm32,reg`, pointer
  tables, jump-table constants; scanned at **step 1**, unaligned included) → **0** for all four cells.
- **B** `movhi imm16` with `imm16 ∈ {0xFEDF, 0xFEE0}` → **0**. *Detector validated*: it finds **7647**
  movhi candidates / 1819 distinct immediates image-wide (`0x00FF`×278, `0xC180`×117, `0x7FFF`×117 …),
  so the null is a fact and not a filter artefact. Nearest immediates are `0xFEE6`(2) and `0xFEFF`(6);
  neither can reach `0xFEDF____` because `movea` adds only a signed 16-bit.
- **C** `movea imm16` equal to each cell's low halfword → 0 for three cells; 22 for `gp-0x6bfe`'s
  `0x1400`, all in the data region above `0xC0000` and all moot because probe B found no `movhi 0xFEDF`
  to pair with.

🛑 **Residual, and it is not closable statically:** a base register built as `mov gp,rX; add k,rX;
st.b r?,0[rX]` is invisible to every operand-text and displacement scan. For a **pure-LOAD** cave this
does not matter — such a writer would already be corrupting the firmware's own use of the cell, and
adding a reader changes nothing. Say it that way rather than claiming the path is closed.

Related: [[reference-accord-v850-6byte-disp-decoder-corrected]] (the 6-byte decoder used here; the only
6-byte accesses among these four cells are the four `gp-0x6752` sites in `FUN_00048a40`, and Ghidra
agreed with Python on all four, `length:6`).
