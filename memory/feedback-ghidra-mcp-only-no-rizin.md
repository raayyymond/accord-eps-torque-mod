---
name: feedback-ghidra-mcp-only-no-rizin
description: "Operator instruction (2026-07-20): GhidraMCP is the ONLY sanctioned disassembler on the Accord EPS kit — no radare2, rizin, r2pipe, or disasm_v850.py. Prime every subagent with this explicitly."
metadata:
  type: feedback
---

On the 2020 Accord EPS firmware kit, **all disassembly and decompilation goes through
GhidraMCP (the `mcp__ghidra__*` tools)**. Do not use radare2, rizin, `r2pipe`, or
`analysis-2020accord/fw_inventory/decompilation/disasm_v850.py` (a CLI-disassembler
wrapper, now retired).

Plain byte-level work on the images — diffing builds, CRC checks, dumping a table,
verifying a table's extent — is Python and is unaffected. The policy governs
*disassembly and decompilation*.

**Why:** the operator interrupted a session to say "no rizin, use ghidra MCP", then
followed up with "make sure this doesn't happen again, remove any rizin or radare from
claude.md". The kit's own docs were the cause: `CLAUDE.md`, the `firmware-decompile`
skill, and the `firmware-codepath-tracer` agent definition all prescribed an
**r2-first tool order**, so subagent briefs inherited it by default. Ghidra's
decompiled C is also simply the better instrument for the structural questions this
kit asks (is this a biquad? is this gain a multiplier or a divisor?), which read far
more directly off pseudo-C than off an instruction listing.

**How to apply:** state the policy explicitly in every subagent brief — the default
instinct is to reach for r2, and a brief that stays silent will get an r2 trace back.
The prescriptions were removed from `CLAUDE.md` (which now carries a "🛑 Tool policy"
section), `.claude/skills/firmware-decompile.md` (rewritten Ghidra-only),
`.claude/agents/firmware-codepath-tracer.md`, and `docs/FIRMWARE-DECOMPILE-GUIDE.md`
(banner marking its r2 sections historical-only).

Historical `docs/HANDOFF-*.md` files and `reference_accord_*` memories still mention
r2/rizin because that is how those findings were obtained. **Leave them** — they are
records, not instructions, and rewriting them would falsify the kit's own history.

Switching tools did not remove the need for corroboration. Ghidra has its own V850
traps — the `divq` dst==src SLEIGH bug, `movhi`/`movea` immediate pairs never
resolved into xrefs, and a recorded case of the xref engine returning a **misleading
zero** on a tp-relative displacement. Any load-bearing null result still needs a
second, independent method. See [[reference-rizin-ghidra-v850-quirks]] and
[[feedback-delegate-firmware-tracing-to-subagents]].
