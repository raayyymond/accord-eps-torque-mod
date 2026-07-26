---
name: v850e2-extended-disp23-encoding-solved
description: SOLVED bit layout of the V850E2 6-byte extended-displacement (disp23) gp-relative load/store — makes a Python byte scan EXACT instead of over-matching 7.6x, closing the kit's known enumeration trap.
metadata:
  type: reference
---

**The 6-byte V850E2 extended-displacement load/store is fully decodable in Python. Use this instead of
matching raw displacement bytes.**

Instruction is 3 little-endian halfwords `hw1 hw2 hw3`:

```
hw1 = (0 << 11) | (op << 5) | reg1        # reg2 field == 0 is the ESCAPE to the extended form
hw2 = (reg3 << 11) | (subop & 0xF) | ((disp & 0x7F) << 4)
hw3 = disp23 >> 7

disp23 = (hw3 << 7) | ((hw2 >> 4) & 0x7F)     # then sign-extend from bit 22
```

For `reg1 = gp = r4`: `hw1 = 0x0704 + 0x20*(op-0x38)`, i.e.
`ld.h = 0x0784`, `ld.hu/ld.bu = 0x07A4`. `reg3 = hw2 >> 11`.

Python:
```python
disp = (hw3 << 7) | ((hw2 >> 4) & 0x7F)
if disp & 0x400000: disp -= 0x800000
target = 0xFEDF8000 + disp          # for gp-relative
```

**Validated 3x against GhidraMCP on `code.bin`, across two opcodes and two displacements:**
- `0x4C784` `84 07 07 6a 61 ff` -> `ld.h -0x4f60, gp, r13` ✓
- `0x5A0C4` `a4 07 07 32 61 ff` -> `ld.hu -0x4f60, gp, r6` ✓
- `0x54034` `a4 07 f5 52 d7 ff` -> `ld.bu -0x1451, gp, r10` ✓

## Why this matters
[[accord-gp4f60-two-encodings-enumeration-trap]] records that a byte scan for this form
**over-matches 7.6x** because `hw3` is shared across ~13 nearby displacements. That is exactly right and
is now explained: **`hw3` only carries `disp[22:7]`, so one `hw3` value covers a whole 128-byte page.**
The fine bits `disp[6:0]` live in `hw2[10:4]`. Decoding `hw2` as well makes the scan exact — no
adjudication pass needed, no over-match, no boundary guessing.

**Corollary — the two blind spots are different things, don't conflate them:**
- A **disp16-only** byte scan misses this 6-byte form entirely.
- `search_instructions` DOES decode this form correctly (it found 7 extended-form `-0x4f60` readers),
  but misses **anything outside an analyzed function body**. On `gp-0x6a46` it returned 20 while a byte
  scan found 24; the 4 missing (`0x2D7D4`, `0x2D902`, `0x2DA8A`, `0x4F97C`) all have **no Ghidra
  function**. That is the 5th recorded occurrence of this undercount on this kit.
- Neither covers **`mov imm32, reg` + register-indirect** pointer passing. Real example: the CAN 0x1D0
  frame buffer `0xFEDF6C20` is read via `mov 0xfedf6c20, r6` (`26 06 20 6c df fe`, 6-byte) at `0x54028`
  and via `movea -0x13e0, gp` passed as an argument — **zero gp-relative reads exist**, so a
  gp-relative scan alone would wrongly call it unread. Catch this with an **LE32 literal scan** of the
  whole image (it is NOT a movhi/movea pair, so a movhi/movea scan misses it too).

⇒ For a load-bearing "who touches X" answer, run **four** methods: disp16 byte scan, disp23 byte scan
(this formula), `search_instructions`, and an LE32 literal scan for the absolute address.
See [[feedback_rigorous_validation]].

## ⚠ SEPARATE TRAP — the 4-byte disp16 form steals `hw2` bit0 for THREE different opcodes
A naive `disp == hw2` comparison is correct **only** for `ld.b`/`st.b`. Per-opcode rules (`reg1` = `hw1 & 0x1F`,
`op = (hw1 >> 5) & 0x3F`, `reg2 = hw1 >> 11`):

| op | mnemonic | displacement |
|---|---|---|
|0x38|`ld.b`|`hw2` (full 16 bits)|
|0x3A|`st.b`|`hw2` (full 16 bits)|
|0x39|`ld.h` if `hw2&1==0`, **`ld.w` if `hw2&1==1`**|`hw2` / **`hw2 & 0xFFFE`**|
|0x3B|`st.h` if `hw2&1==0`, **`st.w` if `hw2&1==1`**|`hw2` / **`hw2 & 0xFFFE`**|
|0x3C/0x3D|`ld.bu`|`(hw2 & 0xFFFE) \| ((hw1>>5)&1)` — LSB lives in `hw1` bit 5|
|0x3F|`ld.hu`|`hw2 & 0xFFFE`|

## 🛑 THIRD TRAP — excluding `reg2 == 0` silently drops every STORE-ZERO (`st.b r0` / `st.h r0`)
`reg2 == 0` is the escape to the 6-byte extended form, so a scan must skip it — **but only for the LOAD
opcodes.** For a store, `reg2` is the SOURCE register and `r0` is entirely legal: `st.b r0, disp16[gp]`
is the compiler's idiom for `var = 0`. Blanket-excluding `reg2 == 0` therefore makes **every
write-of-zero invisible**, which silently understates writer sets and can turn a real writer into a
false "sole writer".

Correct per-opcode rule (`reg1 = hw1 & 0x1F`, `op = (hw1 >> 5) & 0x3F`, `reg2 = hw1 >> 11`):
| op | reg2 == 0 means |
|---|---|
|`0x38` ld.b, `0x39` ld.h/w| skip — dest `r0` is meaningless, so it's the extended escape |
|**`0x3A` st.b, `0x3B` st.h/w**|**KEEP — this is a legal store-of-zero, 4-byte form**|
|`0x3C`-`0x3F` ld.bu/ld.hu| skip — extended escape |

**This bit me for real (2026-07-24, `gp-0x6806` trace):** my scan reported **8** writers of
`gp-0x6806`; the true count is **16**. The 8 missing were all `st.b r0` (`0x29696`, `0x296d2`,
`0x2970e`, `0x29724`, `0x2a80a`, `0x2a842`, `0x2a862`, `0x2a87e`) — and they are exactly the
*disengage* writes, i.e. the semantically decisive half. Same bug hid 2 of 24 `gp-0x69b0` writers.
⚠ Note `st.b r0, disp16[gp]` and the extended-form escape have **byte-identical `hw1`** (both `0x0744`
for op `0x3A`/`reg1=gp`) — they are distinguished ONLY by opcode class, never by `hw1` alone.
✅ Re-running with the fix left `gp-0x6a46` (24 accesses) and `gp-0x6a5e` (1 store) unchanged, so
prior conclusions on those held — but that was luck, not method.

**This bit me for real (2026-07-24):** scanning for the float cell `gp-0x6d14` with `disp==hw2`
returned **0 hits**, yet Ghidra showed `ld.w -0x6d14, gp, r15` at `0x3A002`, bytes `24 7f ed 92` —
`hw2 = 0x92ED`, disp = `0x92EC`. With the correct rule the cell has exactly 1 writer + 1 reader.
**A 32-bit (`ld.w`/`st.w`) cell is invisible to a `disp==hw2` scan.** 16-bit cells accessed by `ld.h`
happen to work, which is why this trap hides — most of this kit's cal/RAM tracing is 16-bit.
⇒ Any "zero writers / zero readers" claim about a **float or 32-bit** cell made with a byte scan must be
re-run with the table above before it is believed.
