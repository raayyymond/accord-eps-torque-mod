---
name: accord-formatv-aliasing-five-false-positives
description: 🛑 A raw byte scan "confirmed" FIVE V850 instructions that do not exist, in one afternoon — all aliases inside 4-byte instructions. Pin every new encoder by three-way field decomposition against Ghidra-confirmed instances.
metadata:
  type: feedback
---

# 🛑 Byte scans confirm instructions that DO NOT EXIST — five in one afternoon

Building V65's cave needed two condition codes and two immediates the kit had never emitted. A raw
little-endian byte scan found plausible donors for each. **Checked in Ghidra, five were aliasing
artefacts sitting inside 4-byte instructions:**

| "found" | actually inside |
|---|---|
| `cmp -0x2,rN` @`0x1A278` | `mov 0x1a27e,lp` |
| `cmp -0x2,rN` @`0x2806A` | a `jarl` |
| `cmp -0x2,rN` @`0x4C12A` | a `dispose` |
| `cmp -0x2,rN` @`0x55FC6` | a `jarl` |
| `bgt +6` (`bf05`) @`0x1BA28` | a `dispose` |

**Why:** V850 mixes 2- and 4-byte instructions with no alignment marker distinguishing them, so any
2-byte pattern will appear inside longer instructions at a rate set purely by the image size. The scan
cannot tell an instruction from the tail of another one. This is the Format-V aliasing trap already on
record — what is new is the **hit rate**: on a short 2-byte pattern it was **5 of 6 candidates wrong.**

## How to pin a new encoder — the method that worked
1. **Prefer a boundary-confirmed instance.** Ask Ghidra for the instruction *at that address* and
   confirm it starts there. V65 pinned `blt +6` (`b605` @`0x1C006`), `bgt +6` (`bf05` @`0x279FC`),
   `bne +6` (`ba05` @`0x14D30`), `be +6` (`b205` @`0x55F76`), `cmp 0x1,r6` (`6132` @`0x14D46`) and
   `ld.h -0x6b94[gp],r6` (`24376c94` @`0x453E0`, **byte-identical**) this way.
2. **If no boundary-confirmed instance exists, decompose the encoding into fields and pin each field
   separately against a different confirmed instruction.** `cmp -0x2,r6` (`7e32`) had none, so it was
   pinned three ways: opcode 0x13 + reg2 r6 with a *negative* imm5 (`cmp -0x1,r6` `7f32` @`0x1BC24`),
   opcode + reg2 with a *positive* imm5 (`cmp 0x1,r6` `6132` @`0x14D46`), and the Format-II imm5 field
   0x1E == −2 (`mov -0x2,r8` `1e42` @`0x50A12`). Plus an arithmetic identity assert.
3. **Assert the near-miss you would have made.** `sar` vs `shr`, `ld.h` vs `ld.hu` (a sign loss that
   silently inverts a signed comparison), `ld.h` opcode 0x39 vs `st.h` 0x3B (a one-bit slip that turns
   a probe's read into a **write into the aggregator output**). Check these *by opcode value*, not by
   eye.
4. **Never let a raw byte scan be the sole confirmation of an instruction's existence.** It remains the
   right tool for the opposite job — enumerating *data* and proving a count or a null, where the kit
   requires it as the second method.

⚠ Note the asymmetry with the recorded `search_instructions` traps: **that** tool under- and
over-counts *analysed* instructions; a **byte scan** hallucinates instructions that were never there.
The two failure modes are different and both are live. Cross-check in the direction that can falsify.

---

## 🛑 A SECOND, DISTINCT TRAP FROM THE SAME BUILD — `hw1` bit 5 means OPPOSITE things

Same session, and this one produced a **wrong statement by the orchestrator that a subagent had to
correct**. For `ld.bu`/`ld.hu`, a displacement's **bit 0 rides in `hw1` bit 5** (it is part of the
opcode field), and **`hw2`'s LSB is the WIDTH selector, always 1**. For `ld.h` (opcode 0x39), `hw1`
bit 5 is **merely the opcode's own low bit and carries NO displacement meaning at all.**

Concrete, byte-read from `_v62_plain_image.bin`:

| instruction | site | `hw1` | bit 5 | what bit 5 means there |
|---|---|---|---|---|
| `ld.bu -0x67ac[gp],r8` | `0x3AA34` | `0x4784` | **0** | disp bit 0 — and `0x67ac` is **even**, so it must be 0 |
| `ld.h  -0x6b94[gp],r13` | `0x3ACEC` | `0x6F24` | **1** | just opcode 0x39's low bit |
| `ld.h  -0x6b94[gp],r6` | `0x453E0` | `0x3724` | **1** | just opcode 0x39's low bit |

**Why it is dangerous rather than pedantic:** encoding `-0x67ac` with `hw1` bit 5 *set* gives
`hw1 = 0x37A4` and silently reads **`gp-0x67ab`** — a **real adjacent cell** (the other fold result,
stored 4 bytes later at `0x2773E` in `FUN_00026c80`). That is a **plausible wrong answer, not a
crash**, which is this kit's worst failure class: a probe that reports confidently about the wrong
variable.

**Rule:** always reconstruct the displacement as `(hw2 & 0xFFFE) | (hw1 bit 5)` and **assert it equals
the intended value as a live gate**, not as a comment — and check the opcode family *first*, because
the same bit position changes meaning between families. If the displacement is even, bit 5 **must** be
clear; if that disagrees with your prose, trust the arithmetic.

★ Prefer a donor whose **register field also matches**: V65's cave `ld.h` (`24376c94`) is
**byte-identical** to the firmware's own read at `0x453E0`, r6 included, so no "reg2 may differ"
caveat is needed anywhere in the gate.

Pairs with [[accord-v850-scan-traps-formatv-and-storezero]] and
[[feedback-episodes-not-windows-and-the-noise-floor]].
