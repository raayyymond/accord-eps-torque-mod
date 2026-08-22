---
name: reference_v850_ghidra_cal_read_rendered_as_function_symbol_trap
description: "NEW TRAP 2026-08-22: Ghidra renders some tp-relative cal reads as FUNCTION-SYMBOL ARITHMETIC (`FUN_000071fe + unaff_tp + 4` for tp+0x7202), so grepping a decompile for the hex offset returns ZERO and the cal looks unread. Cost: the 0xC6202 governor ceiling was mis-described as a x4.65 Q10 gain instead of a MIN. Also records that get_function_by_address / decompile_function / disassemble_bytes ALL fail silently on Ghidra-undefined regions in this image."
metadata:
  type: reference
---

# Ghidra renders cal reads as function-symbol arithmetic — a grep for the offset finds NOTHING

Confirmed 2026-08-22 on stock `code.bin` while pricing the governor ceiling.

## The trap

`FUN_0007b022` reads the governor ceiling cal at `tp+0x7202` (= `0xC6202` = 4762). Ghidra's decompile
renders that read as:

```c
uVar35 = *(ushort *)(FUN_000071fe + unaff_tp + 4);     // line 80 -- this IS tp+0x7202
```

because `0x71fe` happens to collide with a function symbol. **A grep of the decompile for `0x7202`,
`4762`, `0x129a` or `0x6202` returns ZERO HITS on all four.** The cal looks unread. It is not.

Same pattern seen in `FUN_00041464`: `*(short *)(FUN_00007488 + unaff_tp + 6)` is `tp+0x748e` =
`0xC648E` (the fault-injection additive bias, stock 0).

**⇒ The rendering is `FUN_<symbol> + unaff_tp + <delta>`, and the real offset is `symbol + delta`.**

### What it cost
The brief I was working from asserted `0xC6202` applied "a Q10 scale, /1024 -> x4.650390625" to the
`0xC520C` rate-scheduled ceiling. **Wrong.** The truth:

```c
line   84: fVar39 = (float)cal(0xC6202) * 0.0009765625;   // 4762/1024 = 4.650390625   <- a CEILING
line  587: if (fVar44 <= fVar39) fVar43 = max(fVar44,0);  // fVar44 = table_Y/1024
line  590: gp+0x184 = fVar43;                             // = clamp(table_Y/1024, 0, 4.650390625)
line 1100: fVar34   = gp+0x184 * 1024.0;                  // re-encode
line 1112: gp-0x4f64 = round(fVar34), sat [0,65535]
```
The `x 0.0009765625` and the `x 1024.0` **CANCEL EXACTLY**. So `gp-0x4f64 = clamp(table_Y, 0, 4762)` —
4762 is a **MIN/SATURATION in the table's own counts**, never a gain. Consequence: the ceiling swing
top->bottom is **9.30x (4762 -> 512), NOT 10.4x (5325 -> 512)** — the 5325 top is itself capped.
(This kit's `docs/STATE.md` carried the x4.65 gain reading; my own
[[reference_accord_governor_gp0x184_chain]] already had it right as a MIN — the two disagreed for weeks
and nobody noticed, because the grep that would have caught it returns nothing.)

## How to defeat it
- **Never conclude "cal X is unread" from a grep of a decompile.** Confirm with a **raw Python LE byte
  scan** for the load encoding. `tp+0x7202` has **exactly ONE reader image-wide, at `0x7B06A`**
  (`ld.hu 0x7202,tp,r15`, bytes `e57f0372`) — found in seconds by byte scan, invisible to grep.
- Verified `ld/st disp16` encoding for such scans (all checked against Ghidra's own output):
  `hw1 = (reg2 << 11) | (op6 << 5) | reg1`, `hw2 = disp` (`|1` for `.w`/`.hu`/`.bu`);
  op6: `0x38` ld.b · `0x39` ld.h/ld.w · `0x3A` st.b · `0x3B` st.h/st.w · `0x3C/0x3D` ld.bu · `0x3F` ld.hu.
  `gp` = r4, `tp` = r5. Cross-checked on `e5870772` = `ld.hu 0x7206,tp,r16`.

## ⚠ Companion trap: Ghidra has UNDEFINED REGIONS in this image, and every tool fails QUIETLY there
In `code.bin` the ranges **`0x44600-0x45700`** and **`0x6BB08-0x7C800`** have no function objects:
- `get_function_by_address` returns `"No function found"` — **even for `0x4503c`, which
  `decompile_function` decompiles perfectly.** So a null from it means nothing.
- `get_xrefs_to(0x7b022)` returned **`"No references found"` — a FALSE NULL.** A self-validated raw
  Format-V scan found the sole caller at `0x6BC9C`. (Format V: `disp22 = sext(((hw1 & 0x3F) << 16) | hw2)`,
  opcode `(hw1 >> 6) & 0x1F == 0x1E`, target = `PC + disp`. **Self-test it** by reproducing known edges —
  mine reproduced `0x453fe->0x49a90`, `0x414c4->0x4613e`, and `0x22200->0x41464` before I trusted it.)
- **`disassemble_bytes` with `dry_run: true` returns an EMPTY instruction list** for undefined regions
  while still reporting `success: true` and `bytes_disassembled: 168`. It is not a disassembly failure
  you can see — it just returns nothing.
- ⇒ In those regions there is **no sanctioned way to read instructions** without letting Ghidra define
  them (a MUTATING action — ask the operator first). **Do not hand-decode as a substitute**: I tried, and
  my decoder mis-typed a `jarl` (`80ff7a09`) as `ld.bu` because the jarl opcode field is `hw1[10:6]`,
  not `hw1[10:5]` like the load/store group. Hand-decoding is how this kit forms confident wrong answers.

See also [[reference_accord_tp_relative_xref_blindspot_and_parity_trap_2026-08-12]] (the same false-zero
class on tp displacements) and [[reference_v850_search_instructions_base_register_collision_trap]].

## ⚠ Companion trap 2: a Ghidra query with NO explicit `switch_program` answers against whatever blob is current
Live instance 2026-08-22. `list_open_programs` returned **three** programs, and the current one was a
**92-byte scratch blob** another agent had imported, not `code.bin`:
```
code.bin                1048576 B   is_current: FALSE
v105_scratch.bin              20 B  is_current: FALSE
v105_pass1_probe.bin          92 B  is_current: TRUE     <-- every query lands here
```
**A query in that state does not error — it returns an authoritative-looking WRONG answer** (an empty
result, a null xref, "no function found"), indistinguishable from a real negative. This is the same
failure family as the `get_xrefs_to` false null and the undefined-region wrong-function return recorded
above: **the tool answers confidently about the wrong object.**

**Defence:** call `list_open_programs` and confirm `current_program` **before** any query whose result
will be quoted as a fact about stock — the standing brief already says this, and this is what it is for.
⚠ **Do NOT `switch_program` reflexively if another agent may be mid-task** — switching yanks the context
out from under it. Confirm first, then switch deliberately and say you did, or wait.

## ⚠ Companion trap 3: a HEADERLESS scratch blob's FILE OFFSETS are not image addresses
Cost a false alarm on the session's most consequential build, 2026-08-22.

Another agent left a 92-byte scratch file (`v105_pass1_probe.bin`) in the shared scratchpad and imported
it into Ghidra. I decoded its `ld.h` loads, found them at **file offsets 0x00 / 0x0C / 0x2E / 0x3A**, and
mapped those onto the cave base `0xC4B34` as though the blob were a contiguous image of
`cave+0x00 .. cave+0x5B`. That put two changed displacements at `0xC4B64` / `0xC4B70` = the **`b5`** rung,
and I raised an alarm that a rejected lane was being evicted.

**Wrong. The blob was two 46-byte copies of the SAME block — a before/after pair.** Verified byte-exactly:
```
block A (0x00-0x2D) vs block B (0x2E-0x5B): differ in EXACTLY 4 bytes, at block-relative
   +0x02,+0x03 and +0x0E,+0x0F        ->  cave 0xC4B36/37 and 0xC4B42/43  = the b6 operands
A's displacements = 2695 / 2495  (== V104 exactly, the "before")
B's displacements = 6c94 / 9cb0  (the "after")
b5 at 0xC4B64/0xC4B70 = 1e95 / da94, UNTOUCHED in the shipped image
```
⇒ **block B starts at file 0x2E, so ITS offset +0x00 is cave+0x00 — not cave+0x2E.** The blob has no
`0xC4B34` base and no header saying so.

🛑 **The trap: decoding a headerless blob's file offsets as image addresses yields a PLAUSIBLE, SPECIFIC,
WRONG address. It does not error.** This is the fourth member of the same family recorded in this file —
`get_xrefs_to` false nulls, the undefined-region wrong-function return, the current-program trap, and this
— **all four return an authoritative-looking wrong answer rather than a failure.**

**Defences:**
- **Never map a scratch blob onto an image base unless something states the base.** Anchor it instead:
  search the blob's byte sequence *in the full image* (`image.find(blob)`) and use the offset you get; if
  it is not found, the blob is not a contiguous image slice and offset arithmetic is meaningless.
- **Check for internal repetition first** — `len(blob) % n == 0` with two structurally identical halves is
  a before/after pair, not a longer region.
- Prefer diffing the **shipped image** against its base. The image has real addresses; a blob does not.
- ⭐ It was harmless only because **the alarm stopped work rather than changing it.** Raising it was still
  right — but the fix is to anchor before alarming, so the next one costs nothing at all.

