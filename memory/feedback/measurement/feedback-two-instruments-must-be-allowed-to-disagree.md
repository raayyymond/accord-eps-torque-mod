---
name: feedback-two-instruments-must-be-allowed-to-disagree
description: Four tool-zeros and one inverted sign in a single session, every one caught only because a second independent method existed. Includes the NEW ep-relative aliasing trap, which is worse than a zero — it returns a healthy non-zero count that misses 100% of accesses.
metadata:
  type: feedback
---

**Run two independent instruments and let them disagree. Every serious error in the 2026-08-12 session
was caught that way, and none would have been caught otherwise.**

**Why:** a single method that returns a clean-looking answer is indistinguishable from a correct one.
This kit's expensive errors are not noisy — they are *confident*.

## THE INVERTED SIGN THAT NEARLY SHIPPED
`scipy.signal.csd(x, y)` returns **`arg(Y) − arg(X)`**, not the reverse. An agent labelled every
cross-spectrum backwards and recommended **lowering `0xC63AC`** — which would have made the car worse.
**The tell was a REPLICATED ~90° disagreement** with an independent estimator (`Q = −d(gp-0x6b70)/d(T)`
on a different grid with a different bootstrap). A *replicated* offset is a bug signature; a physical
disagreement is noisy. ⇒ **When two estimates differ by a suspiciously round, repeatable angle, suspect
a convention, not the car.**

## FOUR TOOL-ZEROS IN ONE SESSION — the fourth is a NEW CLASS
1. **`get_xrefs_to` tp-relative blind spot** — returns "No references found" for cells with real readers.
2. **`search_instructions` undercounts** — scans only analysed instructions, still reports `truncated:false`.
3. **`movea` + register-indirect** — `operand_pattern="-0x6350\[gp\]"` returned **0 / 183,570 /
   `truncated:false`** on an array with **nine** real accesses.
4. ⭐ **`ep`-RELATIVE SHORT-FORMAT ALIASING — worse than a zero.** An array is based once via
   `movea <off>, gp, ep`, then every access is `sld.*`/`sst.*` off `ep`, carrying **no offset in the
   operand text**. Measured: `-0x62f8` → **15 hits, 14 of them base setups, ZERO actual loads/stores.**
   🛑 **A healthy-looking non-zero count that misses 100 % of the accesses** is more dangerous than a
   zero, because it looks like the search worked.
   **Recipe:** operand-search the offset → those are base setups; scan forward in the same basic block
   for `sld.*`/`sst.*` (index arrives as `add rN, ep`); cross-check with a Python `movea`-immediate
   scan (`hw2 == (−off)&0xffff`, opcode `0x31`, dst `ep`=30); `sld.hu` disp is `disp7×2` = 0..254, so
   `ep` must land within 254 bytes below the target.
⊕ **A FILTERED zero is not a fact:** `operand_pattern="0x0[ep]"` returns 0 because Ghidra renders
operands as `r6, 0x0, ep` — commas, no brackets. Dropping the filter returned them instantly.
⊕ **`hw2 = (disp | 1)`** bit again while hand-writing a build assertion: `0xC63AC`'s reader encodes as
`e5 6f ad 73`, hw2 = **0x73AD**, not 0x73AC. The failing assertion was the check doing its job.

## OTHER INSTANCES FROM THE SAME SESSION
- **`np.gradient(ang, t)` is wrong on these caches** — they carry **1,940 duplicate 0x14A timestamps**,
  which divide by zero and poison the trace with inf/NaN. Differentiate on the uniform grid (median dt
  9.891 ms) or use `rate_c`.
- **Differentiating the 0.1°-quantised angle** gave rates that were all multiples of **10.11 °/s** —
  quantisation, not signal. The car's own `rate_c` channel is the finer instrument.
- **A LERP's address is often its `Y[0]`**: the table header for the PID authority ramp is **`0xC67BE`**;
  everyone spent the session calling the lever `0xC67C8`, which is that table's first Y value. **Anchor
  on the `count` field before naming a table.**
- **`LEDGER_TARGET=V96` KeyErrors in `studies/ledger/ledger_v94_cells.py`'s `matrix` and is SILENTLY IGNORED by
  `grid`** — it prints a V94 grid that looks retargeted. **OPEN, unfixed.**

Links: [[feedback-run-the-control-before-the-measurement]] ·
[[feedback-decompile-first-then-assembly]] · [[accord-v850-scan-traps-formatv-and-storezero]] ·
[[feedback-stale-ghidra-import-defeats-hash-check]]
