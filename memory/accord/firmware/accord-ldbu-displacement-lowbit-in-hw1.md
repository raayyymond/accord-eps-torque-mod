---
name: accord-ldbu-displacement-lowbit-in-hw1
description: The gp/tp-relative byte-load displacement's LOW BIT lives in hw1 bit 5, not hw2 — the kit's "ld.bu -> hw2 == enc|1" rule is WRONG and has been conflating ADJACENT CELLS in every byte-load scan.
metadata:
  type: reference
---

🛑🛑 **THE KIT'S STANDING BYTE-LOAD DECODE RULE IS WRONG.** Confirmed 2026-08-21 with Ghidra's own
SLEIGH decoder, orchestrator-verified, after two agents returned contradictory reader counts for
`0xC64FA`.

**The rule that is wrong** (from `CLAUDE.md` and `accord-v850-scan-traps-formatv-and-storezero`):
> *"`st.b`/`ld.b` → `hw2 == enc` EXACTLY; `ld.bu` → `enc|1`"*

which implies `disp = hw2 & 0xFFFE`. **It is not.**

## THE EVIDENCE — identical `hw2`, different target

| bytes | Ghidra `disassemble_bytes` | target |
|---|---|---|
| `85 67 fb 74` @ `0x35A02` | `ld.bu **0x74fa**, tp, r12` | **`0xC64FA`** |
| `a5 7f fb 74` @ `0x260BC` | `ld.bu **0x74fb**, tp, r15` | **`0xC64FB`** |

Both carry `hw2 = 0x74fb`. **The displacement's low bit is `hw1` bit 5** — byte0 `0x85` (bit5 = 0) →
`…FA`; byte0 `0xa5` (bit5 = 1) → `…FB`.

## THE CONSEQUENCE

**Any gp/tp-relative byte-load scan that matched on `hw2` alone has been silently CONFLATING
ADJACENT ADDRESSES.** This is the first trap in this kit's record that **merges two different cells**
rather than miscounting one — every previous scan trap (Format-V aliasing, store-zero, the wrong
`st.b` opcode, `movea` base + runtime index, a byte written by a wider store) produced a wrong
*count* for the *right* cell.

**Confirmed casualty:** `0xC64FA` was recorded as having **18 readers across 5 functions**,
"cross-validated two ways." It has **8**. The other **10 read `0xC64FB`** — a cal cell nobody has
characterised — all inside `FUN_00025c32` (`0x260BC`…`0x261A2`), using it as an unrolled-loop
counter bound. Both "validations" shared the same blind spot.

⚠ **Suspect every prior "N readers" / "zero writers" claim on a BYTE cell.** In particular
`gp-0x683c`'s reported "zero writers image-wide" — which, if wrong, dissolves the V71c-vs-V88
contradiction over the r24/r26 rate lane.

## THE FIX — the only safe method

**Confirm every byte-load target with `disassemble_bytes`.** A raw Python `hw2` scan is still the
right way to *find* candidates (Ghidra's `search_instructions` undercounts while reporting
`truncated:false`, and matches displacement **text, not base register**, so `tp-0x3814` aliases
`gp-0x3814`) — but the **adjudication must come from the decoder, never from the displacement bytes.**

Related: [[accord-v850-scan-traps-formatv-and-storezero]] · [[accord-gp4f60-two-encodings-enumeration-trap]] ·
[[feedback-decompile-first-then-assembly]] · [[accord-r24r26-live-gain-is-default-lerp]]
