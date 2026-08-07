---
name: feedback-check-own-memory-before-retracing-and-variable-reuse-trap
description: Two compounding mistakes that produced a wrong "0xC63A0 is 0.00 dB / dead-end" claim on FUN_0003a382, corrected by team-lead and independently re-verified.
metadata:
  type: feedback
---

Two things went wrong in one session tracing `FUN_0003a382` (gp-0x6ad6 → gp-0x6ad4), and both are avoidable next time.

**1. I didn't check this agent's own memory before re-deriving from scratch.** `reference_accord_fun3a382_engagement_gated_residual_loop.md` and `reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction.md` already establish that `FUN_0003a382` is a real gain-scheduled PID on `gp-0x4f60 - gp-0x6ad6`. I dove straight into `decompile_function` on a fresh trace and concluded (wrongly) that `gp-0x6ad6` was gate-only. The boot-context instructions explicitly list "your own persistent memory... the accumulated `reference_accord_*` findings" as something to read early — I skipped it under time pressure and paid for it with a retraction.
**Why:** re-deriving a fact this kit already has on file wastes the session and produces a confident-wrong answer a grep would have prevented.
**How to apply:** before decompiling a function whose name/address appears anywhere in `MEMORY.md`'s index, grep the matched memory file(s) first — even mid-task, even under a "quantify this now" directive from an orchestrator. It's faster than a wrong answer plus a correction cycle.

**2. Ghidra decompiler variable-slot reuse defeats a plain `grep`-for-displacement trace.** In `FUN_0003a382`, the variable `uVar19` is bound to `LERP(gp-0x6a5e)` early in the function, then **reassigned** later to `(uint)*(short *)(gp-0x6ad6)` — a completely different, unrelated read. Searching the decompiled text for the literal string `0x6ad6` finds only the two occurrences where that displacement is spelled out (an entry-gate boundary check); it does NOT surface that the *value* flowing through `uVar19`/`uVar24`/`iVar30` a few lines later originates from that same displacement, because the second read reuses an already-declared local rather than introducing a new named variable.
**Why:** this produced "gp-0x6ad6 is gate-only, `0xC63A0` is a dead lever" — reversed by re-reading the same decompile line-by-line, tracing data flow through the local instead of grepping for the address text.
**How to apply:** when a `grep`/text-search over a decompiled function returns a small number of hits for a displacement, don't stop at counting them — read every statement between the first and last hit and track what happens to the *destination variable* of each read, since Ghidra will silently reuse the variable slot for a later, unrelated value once the first read is dead. This is a decompiled-C-level trap, layered on top of (not replacing) the asm-level traps in `accord-v850-scan-traps-formatv-and-storezero.md`.
