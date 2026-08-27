---
name: feedback-rigorous-validation
description: "Joey demands rigorous validation before any action affecting his car's EPS firmware — full byte diffs not spot diffs, ghidra confirmation before flash, multi-agent adversarial review"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f0514f23-e142-4d98-bb7b-9a3084e060ea
---

For Honda EPS firmware work specifically, Joey requires rigorous validation before any flash:
1. **Full byte-level diffs, not pre-specified region diffs.** When I diffed only a pre-listed set of regions in C020 mod vs stock, I missed broader patterns and prematurely concluded "torque_shaping_table is unchanged." Joey corrected: "that's definitely not true — aragon literally said the key was the new table definitions." The fix was to do a true full byte-by-byte diff with everything classified.
2. **Adversarial multi-agent review** for any non-trivial port. Joey explicitly asked to "use subagents using best practice from emergent organization and high output agents." Use the pattern: domain-named specialists (not "Agent 1/2/3"), parallel launch, specific questions per specialist, synthesize independently.
3. **Ghidra confirmation before flash.** Joey said "ghidra before moving on" — even after the table map looked solid via +28 Clarity→Civic mapping verified across 4 known tables, he held flashing pending ghidra disassembly to rigorously confirm the table consumers.
4. **Surface concerns even when satisfying his request.** When he asked for "match c020 exactly," I still surfaced the red-team's clamp downgrade + filter grinding concerns. He pivoted to hybrid based on that surfacing.

**Why:** Bricks are real ([[reference-eps-brick-vfn-thedordo]] — 3 confirmed corpus bricks, vfn bought used EPS, thedordo opened 3 modules with dremel + UART recovery). Pre-emptive optimism on safety-critical car firmware = bad outcome. Joey's working with Aragon on PID tuning and trusts his judgment — but doesn't trust agent enthusiasm or premature pattern matching.

**How to apply:**
- Before declaring "this region/table is unchanged" — verify via full byte diff, not partial-region scan
- Before declaring "ready to flash" — surface every documented concern, even if user already asked for the action
- Build files for Joey to REVIEW, never present as "ready to deploy"
- When subject-matter expert (Aragon) is available, prefer ping-him-first over guess-then-build
- Apply same discipline whenever vehicle-control firmware is involved
