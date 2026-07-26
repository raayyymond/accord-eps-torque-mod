---
name: feedback-build-re-tools-when-needed
description: "Operator (2026-05-28) explicitly authorized building NEW reverse-engineering tooling — Ghidra loaders, processor specs/SLEIGH, analysis/decrypt scripts, custom disassemblers — autonomously when the kit's existing tooling doesn't fit the target. Granted during the addon-radar project where the Bosch radar MCU != SH-2A/V850 so disasm_sh2a.py won't load it. Don't stop at 'tool unsupported' — write the tool."
metadata:
  type: feedback
---

# Build new RE tooling when the target needs it (operator-authorized)

**Granted 2026-05-28** during the addon-radar spec, right after the architecture review flagged that the Bosch FWD-radar firmware (`36802`) is a different MCU than the SH-2A (Civic) / V850 (Accord) EPS — so `disasm_sh2a.py` and the EPS-calibrated decrypt constants won't apply.

**Rule:** When reversing a target whose architecture or container format the kit's existing tooling doesn't cover, **write the new tooling** — Ghidra loaders (e.g. a Honda iHDS `.rwd` container loader), processor specs / SLEIGH, decrypt/analysis scripts, custom disassemblers — rather than treating "the tool doesn't support this" as a blocker to escalate.

**Why:** The operator's lateral-side wins came from deep Ghidra work; he trusts up-front tooling investment to pay off and doesn't want a missing-tool wall to stall the radar/longitudinal RE. He said it directly: "you're an insanely good reverse engineer, so if you need new tools, write new Ghidra tools."

**How to apply:** Inside the R-phase (and any future cross-arch RE), treat tool-building as in-scope work. Still honor the complements: [[feedback-lightweight-inspection-over-ghidra]] — use lightweight Python for simple byte/entropy/signature questions, reserve heavy tool-building for genuine decompile/xref needs; [[feedback-rigorous-validation]] — tooling output still needs full-byte-diff / verification rigor; and the iron rules — offline study is safe, no CAN TX / flash without confirmation.

## Cross-links
- [[reference-honda-bosch-radar-longitudinal-arch]] — the project this was granted for
- [[feedback-lightweight-inspection-over-ghidra]] — the complement (don't over-reach to Ghidra for simple byte questions)
- [[feedback-rigorous-validation]] — built tools still owe full verification
