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

Pairs with [[accord-v850-scan-traps-formatv-and-storezero]] and
[[feedback-episodes-not-windows-and-the-noise-floor]].
