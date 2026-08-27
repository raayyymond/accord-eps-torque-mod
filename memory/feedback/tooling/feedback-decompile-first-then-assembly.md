---
name: feedback-decompile-first-then-assembly
description: "Standing operator instruction 2026-08-04 — always work backwards from the Ghidra decompilation to the assembly, never build an understanding upward from raw bytes."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cd0a7709-d576-4983-bd00-1d8facc96710
  modified: 2026-08-04T23:23:20.369Z
---

🛑 **Standing operator instruction, 2026-08-04:**

> *"When doing our analysis we should work backwards from the Ghidra decompilation/analysis then look
> at the assembly. I think we make a lot more mistakes when starting from the assembly."*

**How to apply.** Start with `decompile_function` / `analyze_function_complete` to establish the
**structure** — what the function computes, which branch is which, what feeds what, where the gates
are. Only then drop to `disassemble_function` / `disassemble_bytes` to pin the exact instruction,
encoding, displacement or byte you now know you need.

⇒ **Assembly is for CONFIRMING a claim you have already framed, and for byte-exact build work. It is
not for FORMING the claim.**

**Why — this is the expensive class of error.** A mis-decoded condition nibble or displacement does not
present as uncertainty; it presents as a **fact**, and it propagates into build specs and flash
decisions. Recorded instances in this kit:
- A `jarl` Format-V scanner mask bug returned **zero hits** for functions Ghidra had just given callers
  for (bits 15:11 are reg2, not opcode; disp sign-extends from 22 bits).
- **`ba05` vs `b205`** — `bne` vs `be` — inverting the meaning of a probe rung.
- `hw2 = (disp | 1)`, and the **odd-displacement `0x3D`-vs-`0x3C`** opcode field, both producing false
  mismatches (see [[accord-v850-scan-traps-formatv-and-storezero]]).
- **2026-08-04, the instance that prompted the instruction:** the orchestrator hand-decoded V71's cave
  from raw bytes, read the seed `203e1000` as putting liveness on **bit4** instead of bit7, and issued
  a re-cut demand against a **correct** build. The decompile showed the structure immediately — a
  5-bit accumulator at weights {0x10,8,4,2,1} plus one `shl 0x3,r7` moving the field into bits 7:3.
  The builder's own account was right and the demand had to be withdrawn.

⚠ **This does NOT relax the existing rules, which still bind:**
- **GhidraMCP is the only disassembler** ([[feedback-ghidra-mcp-only-no-rizin]]).
- **Byte-level work is Python**, and Python is the **required second method** whenever a count or a
  null is load-bearing — `search_instructions` silently undercounts *and* over-counts (substring
  collisions), and a `get_xrefs_to` null is never load-bearing.
- **Re-disassemble from the BUILT image before declaring victory**, and re-import fresh — a stale
  Ghidra import defeats hash-checking ([[feedback-stale-ghidra-import-defeats-hash-check]]).
- Decompiler output has its own traps — it rendered a `ld.h 0x507e[tp],r16` as
  `FUN_0000507c + unaff_tp + 2` because the displacement aliased a real function address. **Structure
  from the decompile; values from the bytes.**
