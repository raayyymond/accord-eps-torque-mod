---
name: reference-rizin-ghidra-v850-quirks
description: Two compounding V850E2-specific decode bugs in rizin 0.8.2 and Ghidra base SLEIGH; suspect tooling first when V850 analysis looks weird
metadata:
  type: reference
source: claude
---

Both rizin 0.8.2's V850 plugin and Ghidra's base `V850:LE:32:default` SLEIGH module have V850E2-specific decode bugs that bit a Honda EPS SA-key analysis hard. Documented here so future V850 work can suspect tooling before suspecting firmware.

## Bug 1: `sld.hu / sld.bu / sld.w` disp scaling

**Symptom:** rizin's printed displacement for short-load instructions is **half** the actual value. Affects `sld.hu`, `sld.bu`, and `sld.w` (probably the whole short-load family).

**ISA-correct decoding:** For `sld.hu rrrrr0000111dddd`, displacement is `bits[3:0] × 2` (halfword-scaled). rizin doesn't apply the ×2.

**Concrete example (from this session):**
- Bytes `70 08` (LE word `0x0870`) at `0x00AABA`
- rizin says: `sld.hu 2[ep], r1`
- ISA-correct: `sld.hu 0[ep], r1`
- So when ep=0x92C0, the load reads from `0x92C0`, NOT `0x92C2`

## Bug 2: `divq reg2 == reg3` semantics

**Symptom:** rizin (and Ghidra base SLEIGH) print `divq` mnemonic correctly but get the result semantic wrong when `reg2` and `reg3` are the same register.

**ISA-correct behavior:** Per V850E2M Architecture Manual: "If reg2 and reg3 are the same register, the **remainder** is stored in that register." So `divq r10, r6, r6` computes `r6 = r6 % r10` (modulo), NOT `r6 = r6 / r10` (quotient).

**Documented in Ghidra:** SLEIGH issue #8995 (NationalSecurityAgency/ghidra). Same bug existed in Ghidra's V850 SLEIGH; PR #1430 (V850E2M from Aleckaj) has the fix.

## Other V850E2 encodings missing from base ISA

Both rizin 0.8.2 and Ghidra `V850:LE:32:default` ship the V850 base ISA only. V850E2-specific 6-byte encodings (notably `cmpib` with opcode `0x061A` and the unsigned-displacement `st.h disp23[reg]` form) decode as `invalid` or misreport. For confirmed cmpib/st.h analysis on V850E2 silicon, decode raw bytes against the V850E2M manual.

## Bug 3 (2026-07-02): radare2's DEFAULT `v850` plugin mis-decodes V850E2 loads — use `v850.gnu`

In a cloud session, radare2 `5.5.0` (installed via apt; rizin/Ghidra were both unreachable — their release downloads are GitHub-hosted and blocked by the environment's proxy). radare2 ships **two** V850 plugins: `v850` (LGPL, `_dAe`) and `v850.gnu` (binutils-2.35-based, `_d__`). **The default `v850` plugin MIS-DECODES V850E2 `ld.hu`/`ld.w` disp16 loads** — it rendered the gentle-EME decider `FUN_00040d58`'s `ld.hu 0xNNNN[rX]` instructions as bogus `setf`/`xori` clusters (the branch skeleton and 2-byte ops still looked right, which is the trap). Switching to **`v850.gnu`** (`r2 -a v850.gnu …` or `e asm.arch=v850.gnu`) decoded them correctly (`ld.hu 29458[r5], r7` etc.), cross-checked by raw-byte decode of the `reg2`/`reg1`/`disp` fields. Note `v850.gnu` still inherits the base-ISA gaps (Bugs 1–2 above), so raw-byte-verify `sld.*`/`divq` regardless. Ghidra headless would work here (JDK 21 present) **if** GitHub is ever allowlisted; until then radare2-via-apt + `v850.gnu` is the reachable path. **Signature of this bug: a function body that decodes as a run of `setf`/`xori` where you expect `ld.hu`/`ld.w` cal reads → switch to `v850.gnu` before suspecting the firmware.**

## Operational rule

**When V850 analysis produces a "this looks like a different algorithm" finding, default-suspect the tooling before default-suspect the firmware.** In this session, both bugs above compounded to make the universal Honda EPS algorithm look like a 2-constant divide variant. With correct decode, it was the standard 3-constant `(seed+k0)^(seed*k1)%k2` formula. Always cross-reference rizin output against the V850E2M ISA before claiming algorithmic novelty.

## Authoritative references

- [Ghidra V850E2M SLEIGH PR #1430 (Aleckaj)](https://github.com/NationalSecurityAgency/ghidra/pull/1430)
- [Ghidra issue #8995 — V850 SLEIGH division bugs](https://github.com/NationalSecurityAgency/ghidra/issues/8995)
- [binaryninja-v850 (ehntoo)](https://github.com/ehntoo/binaryninja-v850)
- [Renesas CS+ divq reference](https://tool-support.renesas.com/autoupdate/support/onlinehelp/csp/V4.01.00/CS+.chm/Compiler-CCRH.chm/Output/ccrh05c0902y1700.html)
- Renesas R01US0001EJ0100 (V850E2M ISA reference)

**Audit trail:** `analysis-2020accord/V850_ALGORITHM_VERIFIED.md` (bit-level audit), `analysis-2020accord/V850_TOOLING.md` "Known disassembler quirks" section, `analysis-2020accord/disasm_v850.py` docstring.

**How to apply:** Whenever running rizin or Ghidra base SLEIGH against V850E2 firmware, raw-byte verify any `sld.*` disp value and any `divq dst==src` instruction before trusting the output. Use `analysis-2020accord/disasm_v850.py` for V850 work in this kit but be aware of these limitations.
