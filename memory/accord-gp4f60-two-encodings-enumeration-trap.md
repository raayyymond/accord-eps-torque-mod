---
name: accord-gp4f60-two-encodings-enumeration-trap
description: "gp-relative accesses exist in TWO encodings (4-byte disp16 and 6-byte extended-disp) — a disp16-only byte scan silently undercounts, which invalidated the \"definitive 69 readers\" figure."
metadata: 
  node_type: memory
  type: reference
  originSessionId: ad5622d6-5208-450c-86c6-9dd849c09dd4
  modified: 2026-07-24T20:45:14.595Z
---

**Any "N accesses, fully enumerated" claim for a gp-relative variable must state that it covered BOTH
encodings.** A scan of only the 4-byte form silently misses readers and reads as authoritative.

**Encoding 1 — 4-byte gp-relative disp16** (the one everyone scans for):
`hw0 = (reg2<<11) | (opcode<<5) | reg1`, `reg1 = 4` (gp); `hw1` = the disp16.
`ld.h` = opcode 0x39 (disp bit0=0), `ld.hu` = disp bit0=1, `st.h` = 0x3B.
For gp-0x4f60: `hw1 = 0xB0A0`. Highly specific → a byte scan on this form is RELIABLE.
Verified counts for gp-0x4f60 in V38: **64 `ld.h` + 5 `st.h`**.

**Encoding 2 — 6-byte V850E2 extended displacement** (the blind spot):
`hw0 = 0x0784` (ld.h) or `0x07a4` (ld.hu) — i.e. `reg1 = 4` (gp), opcode field 0x3C/0x3D.
**Destination register = `(hw1 >> 11) & 0x1F`.** Worked example, byte-verified:
`0x4C784 = 8407 076a 61ff` → `ld.h -0x4f60[gp], r13`.

⚠ **CORRECTED FORMULA — an earlier version of this memory said `(hw1 >> 3) & 0x1F`. That is WRONG:
it returns `r0` for all 7 known-good sites.** The confusion came from doing the arithmetic on the
HIGH BYTE (`0x6a >> 3 = 13`, which happens to be right) and then writing it down as a shift of the
whole halfword. `(hw1 >> 11) & 0x1F` reproduces all 7 real registers exactly.

⚠⚠ **`hw2 = 0xff61` is NECESSARY BUT NOT SUFFICIENT for `-0x4f60`.** It does NOT encode the full
displacement — it is shared across ~13 nearby displacements (`-0x4f60, -0x4f68, -0x4f6a, -0x4f6c,
-0x4f6e, -0x4f70, -0x4f74, -0x4f78, -0x4f7a, -0x4f08, -0x4ee8, …` — a dense struct/array region).
Scanning on `(hw0, hw2)` alone returns **53 hits of which only 7 are gp-0x4f60 — a 7.6× over-match.**

So byte scanning ALONE cannot enumerate encoding 2. **Every candidate must be confirmed by Ghidra's
semantic decode** (`disassemble_function` on the containing function, or `search_instructions` with
`mnemonic=ld.h/ld.hu` + `operand_pattern`), not by hand-decoding `(hw0, hw2)`.

Note the same ambiguity bites length-decoding: `jr/jarl disp22` (`0x0780` family, 4 bytes) and the
48-bit ext-disp load (`0x0784`) share their high bits and differ only in the low 5 bits, which double
as displacement bits for `jr`. A single-guess instruction-length function will mis-size one of them —
this wrongly rejected a valid boundary at `0x3B908` in `verify_v52c_image.py` until the walker was
changed to search over ambiguous lengths.

**CORRECTION OF RECORD — final, triple-method:** the figure "gp-0x4f60 has 64 raw readers / 69
accesses, definitively enumerated" (2026-07-24 handoff) is **WRONG** — it covered only encoding 1.

| encoding | ld.h | ld.hu | st.h | subtotal |
|---|---|---|---|---|
| disp16 (4-byte) | 64 | 0 | 5 | 69 |
| extended (6-byte) | 6 | 1 | 0 | 7 |
| **TOTAL** | **70** | **1** | **5** | **76** |

**76 accesses = 71 loads + 5 stores.** All 7 encoding-2 readers are in `FUN_0004c780` (boot self-test,
table-dispatched via the 0xBBA18 literal), `FUN_00059912`, and `FUN_00059e7a` (UDS/RDBI record
packers). **None is a command-path carrier** — every one writes only to a local output buffer
(`sst.b rX,N[ep]` / `st.b rX,N[r26|r28]`), never to a `gp-0x69xx/0x6axx/0x6bxx` command cell. So the
19-carrier partition is COMPLETE. **No 6-byte STORE exists** — the single-producer chain
(`FUN_0007ec34`→`FUN_0007f3f8`) remains the only writer, all 5 stores disp16.

⚠ **`search_instructions` also undercounted encoding 1** — it returned 61 `ld.h` where a raw byte scan
returns 64. The 3 it missed (`0x2D9A2`, `0x2DAE6`, `0x4F996`) are real, valid instructions that sit
OUTSIDE any function boundary (`get_function_by_address` → "No function found"), so the tool skipped
them: it only walks function-owned instructions. **4th recorded occurrence of that blind spot.**

**Neither tool is trustworthy alone.** Raw byte scan misses encoding 2 and over-matches it 7.6×;
`search_instructions` misses instructions outside function boundaries. The reliable recipe is: raw
byte scan for encoding 1, `search_instructions`+Ghidra semantic decode for encoding 2, and
cross-check the two. See [[accord-v52c-complete-broad-lowpass]].

---

## 🛑 2026-08-10 — THE INDEXING IS 0-BASED, AND APPLYING IT 1-BASED VOIDS THE SCAN

`CLAUDE.md` carries the one-liner `disp = (sext16(hw2)<<7) | ((hw1>>4)&0x7F)`. **In that formula
`hw1` and `hw2` are the SECOND and THIRD halfwords** — this file is 0-indexed (`hw0` is the first).
An agent this session read them as the *first two*, got only garbage candidates, and wrote a
confident **"no evidence the second encoding is used"** into a trace report. Every "no 6-byte form"
null it produced was VOID.

**Unambiguous, spelled out.** For a 6-byte access at address `A`:
```python
hw0 = u16le(buf, A+0)     # 0x0784 = ld.h  |  0x07a4 = ld.hu   (reg1 = 4 = gp)
hw1 = u16le(buf, A+2)     # destination register = (hw1 >> 11) & 0x1F
hw2 = u16le(buf, A+4)
disp = (sext16(hw2) << 7) | ((hw1 >> 4) & 0x7F)
```
Worked example, byte-verified: `0x4C784 = 84 07 07 6a 61 ff` ⇒ `hw0=0x0784, hw1=0x6a07, hw2=0xff61`
⇒ `sext16(0xff61) = -159`, `-159<<7 = -0x4F80`, `(0x6a07>>4)&0x7F = 0x20` ⇒ **`disp = -0x4F60`** ✅
and `(0x6a07>>11)&0x1F = 13` ⇒ **`r13`** ✅. Validated: reproduces all 7 of Ghidra's 6-byte
`gp-0x4f60` hits exactly, and finds **12 further 6-byte accesses to `gp-0x6b98`** at `0x59a44`–`0x5a0aa`.

## 🛑🛑 AND NEITHER TOOL ALONE IS COMPLETE ON THIS PROGRAM — set-difference them

Fresh reproduction, 2026-08-10, adjudicated site by site:
- **`search_instructions -0x4f60` returned 73 with `truncated:false`.** A raw Python scan found
  **3 more** — `0x2d9a2`, `0x2dae6`, `0x4f996` — all valid `ld.h -0x4f60[gp]`.
  `get_function_by_address` says **"No function found"** for all three ⇒ they sit in **unanalysed
  regions**, which is precisely what `search_instructions` cannot see.
- Conversely, a naive Python scan misses the **6-byte form** that Ghidra decodes semantically.

⇒ **Ghidra sees what Python misses (the 6-byte form); Python sees what Ghidra misses (unanalysed
regions). A load-bearing enumeration needs BOTH, set-differenced, with every disagreement
adjudicated individually.** Neither "Ghidra says N, `truncated:false`" nor "the byte scan is
exhaustive" is sufficient on its own, and both have been quoted as if they were.
