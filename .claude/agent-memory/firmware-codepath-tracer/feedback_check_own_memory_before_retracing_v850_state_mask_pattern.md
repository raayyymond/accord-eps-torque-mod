---
name: feedback_check_own_memory_before_retracing_v850_state_mask_pattern
description: The "andi 0xNNN,r25" one-hot state-mask idiom (r25 = 1 << (gp-0x67fa & 0xf), tested against masks like 0xC30/0xD30/0x930/0x830) recurs across many call sites in FUN_0002214a. A prior session already retracted a "16-phase duty cycle" misreading of this EXACT idiom on one site (2026-08-07); I independently re-derived and initially believed the same wrong "phases" framing on a NEW site (0xD30 gating FUN_00041464/FUN_0004503c) before catching myself by searching for corroboration. Requested explicitly by team-lead to be recorded so a third tracer does not repeat it.
metadata:
  type: feedback
---

# Check memory for the `gp-0x67fa` one-hot state-mask idiom BEFORE forming a "phase divider" hypothesis

**Why:** On 2026-08-22, tracing whether `FUN_00041464` (a filter) and `FUN_0004503c` (the governor
clamp) run unconditionally at 1kHz, I found their calls inside `FUN_0002214a` gated by
`andi 0xD30,r25,r23 / be skip`, with `r25 = 1 << (gp-0x67fa & 0xf)` computed a few lines earlier. **My
first-pass framing was "a cooperative multi-rate scheduler phase mask"** — i.e. I believed this divided
the 1kHz tick into sub-rates for different peer subsystems, and reported (briefly, before catching it)
that this implied a slow ZOH effect worth chasing as a candidate 0.3-3Hz mechanism.

**This is the EXACT misreading a prior tracer session already made and retracted**, on a DIFFERENT
`andi` site in the same function family — see
`.claude/agent-memory/firmware-codepath-tracer/reference_accord_gp67fa_vs_gp63fd_mode_domain_and_v75_cave_reverse_engineered.md`
(2026-08-07): *"I had proposed streaming `gp-0x67fa == 26`... **This is wrong**... `gp-0x67fa` is used
ONLY via its low nibble against small bitmasks — consistent with 167 confirmed program-wide read/write
sites... essentially all plain byte compares against small integers."* And the fuller state-graph memory
(`analysis-2020accord/.claude/agent-memory/firmware-codepath-tracer/reference_accord_state4_ratchet_and_gp67fa_state_graph.md`)
explicitly notes: *"A prior session's '16-phase duty cycle' reading of `gp-0x67fa` was already retracted
before this session."* **That's at least two prior corrections of the identical idiom, on different
sites, before mine.**

I caught my own version only because I went looking for corroboration on the specific NEW mask (`0xD30`)
I'd found — cross-referencing `docs/archive/LEDGER-V38-TO-V84.md` and the memories above revealed `0xD30 = 0xC30
| 0x930`, a UNION of two ALREADY-DOCUMENTED per-STATE masks (`0xC30`=aggregator, `0x930`=arbitration),
not a novel phase divider at all.

**How to apply:** Before framing ANY `andi <mask>,rX,r0` / `shl`/`1<<` idiom on `gp-0x67fa` (or any
similar low-nibble-derived one-hot test) as a "tick phase" or "scheduler divisor," **grep memory first**
— `grep -rl "67fa" memory/ docs/ .claude/agent-memory/` — this codebase's RTOS-adjacent bitmask idioms
are STATE tests far more often than phase dividers, and this specific instance has already fooled this
kit's tracers at least twice. The general form of the trap: a `1 << (byte & 0xf)` one-hot test looks
structurally identical whether the byte is a rotating phase counter or a state-machine value — only
checking the byte's OWN writer (does it rotate every tick, or does it change on discrete state
transitions gated by unrelated conditions?) distinguishes them, and that check is cheap relative to the
cost of re-deriving and reporting the wrong framing.

## Related
[[reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof]] — the trace this lesson came out
of; the corrected state-gating finding (chain is live during ordinary driving, state 5 dominates) is
there.
