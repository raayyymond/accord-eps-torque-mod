---
name: reference_v850_ep_relative_short_format_aliasing_trap
description: "NEW TRAP CLASS, 2026-08-12: a gp/tp array based once via `movea <off>, gp, ep` is then accessed by short-format sld.*/sst.* off ep, which contain NO trace of <off> in operand text. An operand search returns the base-setup sites only -- a healthy-looking NON-ZERO count that misses 100% of the actual accesses. More dangerous than a zero, because a zero prompts suspicion and a plausible count does not. Includes the enumeration recipe and the 254-byte reachability bound."
metadata:
  type: reference
---

# `ep`-relative short-format aliasing — the tool-zero that doesn't return zero

Found 2026-08-12 (`fw-return`) while enumerating the 11-channel LKAS request arrays. Team-lead asked
for it to be carried into the `firmware-decompile` skill.

## The trap

A `gp`/`tp`-relative array is addressed **once** by `movea <off>, gp, **ep**`, after which every real
load/store uses the **short format** — `sld.h/sld.hu/sld.b/sld.w`, `sst.h/sst.b/sst.w` — with a small
displacement off `ep`. **Those instructions contain no trace of `<off>` in their operand text.**

An operand search for `<off>` therefore returns the **base-setup sites only**: a plausible, non-zero
count that makes the census *look* like it worked while missing **100 % of the accesses**.

> 🛑 **A census that returns 15 sites and misses every actual access is more dangerous than one that
> returns 0.** A zero prompts suspicion; a healthy-looking count does not.

Measured: `search_instructions("-0x62f8")` → **15 hits, 14 of them `movea …, gp, ep`, and ZERO actual
loads/stores.** The real accesses are `sst.h r14, 0x0[ep]` @`0x26496` and friends.

## Enumeration recipe

1. Operand-search the offset → collect `movea <off>, gp|tp, ep`. **Base setups, not accesses.**
2. Scan forward in the same basic block for `sld.*`/`sst.*` — those are the real accesses. The index
   arrives as `add rN, ep` between the `movea` and the access.
3. Cross-check the base-setup list with a Python scan: `hw2 == ((-off) & 0xffff)`, `hw1` opcode field
   `0x31` (`movea`), `reg1 = gp(4)`/`tp(5)`, `dst = ep(30)`. This reproduced Ghidra's 15 one-for-one.
4. **Reachability bound** — to ask *"can address X be reached this way at all?"*: `sld.hu` displacement
   is `disp7 × 2` = 0..254, so `ep` must land within **254 bytes below X**. Enumerate
   `movea imm, tp, ep` (`hw1 = 0xF625`) and test whether any `imm ∈ [off−254, off]`.
   ⊕ `gp`-based `ep` **cannot** reach the `0xC4000-0xC7FFF` cal block at all — `movea` is ±32768 from
   `gp = 0xFEDF8000`. So for cals, only `tp`-based `ep` matters, and that scan is small (98 sites
   image-wide).

## Two sibling false zeros confirmed the same day

- **`operand_pattern` syntax**: `search_instructions(mnemonic="sst.b", operand_pattern="0x0[ep]")` →
  **0 matches, `truncated:false`**. Ghidra renders the operands as **`r6, 0x0, ep`** — commas, no
  brackets. Dropping the operand filter returned them immediately. **A filtered zero is not a fact**;
  re-run unfiltered or function-scoped. Same class as the `gp-0x6b98` "zero writers" incident.
- **`operand_pattern="0x7cd0"`** → **0, `truncated:false`** for `0xC6CD0`, a cal this kit has written
  on seven builds. It is real — it simply has **no direct `tp`-relative reader**, because it lives
  inside a LERP table reached by a table-base pointer. ⇒ "no direct reader" ≠ "dead cal".

## Which censuses this does and does not touch

| census | affected? |
|---|---|
| request arrays `gp-0x62f8/62e0/62b0/6298/62c8/633c` | **YES** — enumerate base setups only, and say so |
| `0xC63AC` (1 reader / 0 writers) | **NO — re-tested clean**: 98 `movea imm,tp,ep` sites, **0** within 254 B |
| aggregator zero-reject map | NO — `addi`/`cmovc` mnemonic search inside one function |
| `gp-0x37ba` no-non-zero-writer | NO — scalar, direct `gp` form, no `movea …, ep` |
| direct `tp`-relative cal reads (`ld.hu <off>, tp, rN`) | NO |

## Related
[[reference_accord_two_lkas_routes_gp6b4c_bypasses_auth]] — the trace that surfaced it.
[[reference_accord_tp_relative_xref_blindspot_and_parity_trap_2026-08-12]] — the other tool-zero classes.
