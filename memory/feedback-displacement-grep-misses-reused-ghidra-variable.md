---
name: feedback-displacement-grep-misses-reused-ghidra-variable
description: Grepping a decompile for a gp-displacement finds only the first binding — Ghidra reuses variable slots, so a second read of the same cell can feed a live data path the grep never shows.
metadata:
  type: feedback
---

🛑 **A text-grep for a `gp-`/`tp+` displacement inside a Ghidra decompile is NOT a census of that
cell's uses in the function.** Ghidra reuses variable slots. Once `uVarN = *(short *)(gp - 0xNNNN)`
binds the value to a name, **every downstream use appears as `uVarN`, not as the displacement** — so a
grep for `0xNNNN` shows the load and nothing after it. If the same slot name was *already* used
earlier for an unrelated quantity, a reader tracing by name is also silently misled.

**How it cost this kit a wrong decision-bearing answer (2026-08-07).** A tracer grepped
`FUN_0003a382` for `-0x6ad6`, found two hits — both inside the entry gate
`if (|gp-0x6ad6| > 0x6400 || |gp-0x4f60| > 0x6400)` — and concluded *"`gp-0x6ad6` is a GATE input,
never a DATA input, therefore reverting `0xC63A0` changes delivered damping by **0.00 dB**, and
`FUN_0003a382` is not a PID."* All three claims were false, and it **reversed the tracer's own
correct earlier report** to get there.

The decompile actually has **three** occurrences. The third,
`uVar19 = (uint)*(short *)(gp - 0x6ad6)`, is a live data read — and `uVar19` had **already been used
earlier in the same function** for `LERP(gp-0x6a5e)`, so the reassignment did not stand out. It feeds
`uVar24` → `iVar30 = gp-0x4f60 − uVar24` → the ±0x2800-clamped **error** `iVar31` → three
gain-scheduled P/I/D lanes → `gp-0x6ad4`. ⇒ `gp-0x6ad6` is the **PID feedback term**, and
`FUN_0003a382` **is** a gain-scheduled PID, exactly as the golden model already said.

**The rule:** to establish that a cell is *only* a gate / *only* a boundary check — a **null result**,
and null results in this kit are load-bearing — you must **read the function body and follow the
binding**, not grep the displacement. Nulls need a second method
([[accord-v850-scan-traps-formatv-and-storezero]] makes the same point for `search_instructions`).

**Two orchestrator lessons, both already standing rules that paid off again:**
- **Decompile first, then assembly** ([[feedback-decompile-first-then-assembly]]) — the structure was
  visible at a glance in the decompile; the grep was a shortcut *around* reading it.
- **Verify the crux yourself** ([[feedback-verify-the-crux-yourself-it-caught-four-errors]]) — this was
  caught only because the orchestrator re-read `FUN_0003a382` instead of relaying the claim. ⚠ Note
  the orchestrator had **already propagated the error into the golden model** before checking, and had
  to revert it. **Check before you write it down, not after.**
- ⊕ A subagent **reversing its own earlier correct finding** deserves extra scrutiny, not less — the
  confidence of a "correction" reads as diligence and is easy to accept unchallenged.

Related: [[feedback-decompile-first-then-assembly]] ·
[[feedback-verify-the-crux-yourself-it-caught-four-errors]] ·
[[accord-v850-scan-traps-formatv-and-storezero]] · [[accord-v77-cannot-reach-the-monitors]]
