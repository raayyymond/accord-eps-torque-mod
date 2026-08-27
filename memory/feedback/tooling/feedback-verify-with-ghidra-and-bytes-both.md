---
name: feedback-verify-with-ghidra-and-bytes-both
description: Standing operator instruction — verification requires BOTH Ghidra decompilation/analysis AND a raw byte read. One method alone is not verification.
metadata:
  type: feedback
---

🛑 **Standing operator instruction, 2026-08-05: verification is done with Ghidra decompilation AND
analysis, *and* with byte verification. Both. Every time.**

A byte diff that matches the manifest proves the *bytes* are what you intended. It does **not** prove the
CPU decodes them as the instructions you intended, that the edited cell is the one the code actually
reads, or that a cave's control flow is what the build script's comments claim. A Ghidra decompile proves
structure but is read from a **possibly stale import** and not from the artifact you are about to fly.
**Neither method alone closes the gap. Run both, on the built image, and say so.**

**Why:** this kit's expensive errors have all lived in the gap between the two methods.
- V72's damping levers were **byte-perfect and CRC-clean** and the car never read the table — a pure byte
  check passed a lever that was structurally inert (`[[reference-accord-car-is-tvca4-mode-24-26]]`).
- A `ba05`/`b205` (`bne` vs `be`) mis-decode inverted a probe rung's meaning; the bytes were "right".
- An orchestrator hand-decoded a cave from a hex dump and nearly declared a correct build broken —
  the decompile showed the structure at a glance (`[[feedback-decompile-first-then-assembly]]`).
- ⚠ And the converse: a **stale Ghidra import defeats hash-checking**, so a re-disassembly that was not
  re-imported from the built artifact proves nothing
  (`[[feedback-stale-ghidra-import-defeats-hash-check]]`).

**How to apply — before declaring any build verified, or any claim about firmware settled:**
1. **Byte side.** Full byte diff (never a spot diff) of the **built image** vs its base and vs stock;
   re-read every edited cell back **from the built artifact**; confirm the keep-list is byte-identical;
   confirm CRC/trailer extents. Python, little-endian.
2. **Ghidra side.** **Import the built image fresh** — do not trust an open program. Then
   `decompile_function` / `analyze_function_complete` for **structure** first, and only then
   `disassemble_function` / `disassemble_bytes` to pin an exact instruction, encoding or displacement.
   For a cave: re-disassemble it **from the built bytes** and confirm the control flow, the condition
   nibbles, the load widths and the store target.
3. **Reconcile them explicitly.** State both results. If they disagree, the disagreement *is* the finding
   — stop, do not pick the convenient one.
4. **Say which method produced which claim** when reporting, so the operator can check the crux.

⊕ This composes with, and does not replace, `[[feedback-decompile-first-then-assembly]]` (structure before
assembly) and the orchestrator rule that a decision-bearing subagent claim is never relayed as fact
without confirming the crux yourself.
