---
name: feedback-lightweight-inspection-over-ghidra
description: "For simple byte-level questions (endianness, entropy, signature density, region scans), Joey wants lightweight Python/PowerShell scripts over the Ghydra MCP, which is token-heavy"
metadata:
  node_type: memory
  type: feedback
---

Joey's preference (stated 2026-05-23): **reach for raw-file Python/PowerShell scripts before the Ghydra MCP for simple inspection.** The Ghidra MCP (`mcp__ghydra__*`) is token-heavy — each `memory_read`/`functions_disassemble` is a network round-trip and the listings are verbose. For questions that are really about bytes, a few lines of Python over the on-disk `.bin` answers them at a fraction of the cost.

Concretely, do in a script (not MCP):
- endianness / ISA discrimination (e.g. LE vs BE int16 axis monotonicity; instruction-signature density like V850 `0x0780` jr-opcode count vs SH-2A `0x4F22` prologue / `0x000B` rts count)
- entropy analysis, programmed-vs-`0xFF` region maps, byte histograms
- pointer-table in-range validation, string/offset scans, CRC checks

Reserve Ghydra for what genuinely needs it: the **decompiler** (C output), the **xref database**, and named-function/structure work. Even then, note this build's quirks: `memory_disassemble` returns "Done" with no listing (broken); `functions_create` doesn't disassemble the new function body; `functions_*` only work on already-defined functions.

**Why:** the Pilot-ISA question (V850 vs SH-2A) was settled in one Python pass comparing signature densities across both `.bin`s — the equivalent in MCP calls would have been dozens of verbose round-trips. Joey flagged the token cost directly.

**How to apply:**
- Default to `python` (anaconda env `bin_decompile`) over `code.bin` / decoded `.bin`s for any byte/endianness/entropy/signature/region question.
- Use the Ghidra MCP when you need decompilation, xrefs, or to operate on named functions — and confirm which instance/file you're on first (see [[reference-pilot-tg7-is-v850]] for how easy it is to be looking at the wrong program/processor).

**Update 2026-05-25 — scoped override for C120 mapping campaign:** Joey installed the hackleaf/GhidraMCP v5.2.0 fork (193 MCP tools — much broader than the earlier build this memory was written against) and explicitly directed: "use Ghidra MCP for everything this round because it's wildly enhanced." For the swarm-driven C120 deepening work (see `docs/swarm-specialists/`), default to MCP-first. The token-cost concern from the original build is reduced by the v5.2.0 tool ergonomics. Re-evaluate this override per-campaign — the lightweight-Python preference remains the long-run default outside this specific work.
