---
name: feedback-default-maximal-thoroughness
description: Standing operator instruction (2026-07-22) — default to MAXIMAL thoroughness on every task WITHOUT being asked and WITHOUT checkpointing for permission between analysis steps. Run every analysis thread to completion, close every open gate, verify subagent work at the byte level, build the ready UNFLASHED candidate with the full verification harness, and keep the golden model + memories + a handoff doc current as you go. Do NOT present an "a/b/c, which do you want?" menu for analysis/prep work — just do all of it. The flash / CAN / UDS safety gates are the ONLY hard stops and are NOT relaxed by this.
metadata:
  type: feedback
---

# Default to maximal thoroughness; do not checkpoint for permission on analysis/prep

**Standing operator instruction (2026-07-22, recorded so it need not be repeated):** on this kit, DEFAULT
to doing *everything* thoroughly and autonomously. Do not stop to ask which subset of the open analysis to
do — do all of it, then report.

**How to apply, every session:**
- When multiple analysis threads or gates are open, **close all of them.** Do NOT offer an
  "(a)/(b)/(c) — which do you want?" menu for *analysis or build-prep* work. Run every thread the decision
  needs: GATE-2 Nyquist sweeps, task-rate traces, branch sims, loop-fraction bounds, sensitivity sweeps, etc.
- **Verify subagent work at the byte level** — re-derive their load-bearing numbers, re-run their scripts,
  byte-read the addresses they cite. The operator has said this repeatedly; it is part of "thorough."
  See [[feedback_rigorous_validation]] and [[feedback-delegate-firmware-tracing-to-subagents]].
- **Build the ready UNFLASHED candidate** and run the full verification harness (byte-exact diff, 50-block
  CRC chain, RWD round-trip, Ghidra re-disasm of any code edit) so the artifact is ready the instant its
  gate clears. This is the kit's established "BUILT + verified, UNFLASHED study artifact" pattern (V44–V48A).
- **Do NOT ask permission to build an RWD — just build it** (operator, 2026-07-24). Building an unflashed
  `.rwd`/probe is prep, not a flash; asking "should I build X?" is the checkpoint the operator is telling you
  to skip. Build it, verify it, present it ready. (Only the FLASH/CAN/UDS send remains gated — see below.)
- **Auto-resolve swarm/review-flagged items; don't hand them back as a menu** (operator, 2026-07-24). When an
  adversarial swarm or code review comes back with a FAIL or a flagged residual — a "conditional-safe" open
  trace, a "stable but <caveat>" finding, a "one-way ratchet"/bias, a falsified record claim — go clear it
  autonomously (build the next probe, trace the open readers, fold in the fix, correct the record), then
  report the resolution. Do NOT surface each flag as an "a/b/c, which do you want?" question.
- **Keep records current AS YOU GO**, not only at close-out: the golden models `eps_lkas_chain_model.py` /
  `eps_loop_gain_model.py`, the relevant `memory/` files + `MEMORY.md` index, and a `docs/HANDOFF-*.md`.
- **Apply the two cave/dynamics gates** proactively, every time
  ([[feedback-cave-two-gates-ram-ownership-and-closed-loop]]).

**Why:** firmware RE here is a no-false-summits domain; the operator has been burned by 10+ on-car nulls and
a near-catastrophic brick (V48B), and wants every gate closed and every claim verified BEFORE a decision —
not a checkpoint at each step. Half-done analysis that punts the decision back is the failure mode to avoid.
Thoroughness is the default, not a thing to be requested.

**★ The hard boundary this does NOT cross.** Thoroughness autonomy covers ANALYSIS, BUILD-PREP, and
RECORDING only. It does **NOT** authorize flashing an `.rwd`, running `eps-update*.py`, or sending any
CAN/UDS message. Those remain gated on an explicit operator instruction that names the file + the bus (the
iron rule; CLAUDE.md safety rules 1/2/6). "Do everything to be thorough" means **build it and prove it
ready**, never **flash it**. When the only remaining step is a flash or a CAN/UDS send, STOP and hand it to
the operator with the exact payload/file named for their confirmation.
