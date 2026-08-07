---
name: feedback-verify-the-crux-yourself-it-caught-four-errors
description: 2026-08-06 — the orchestrator's own byte/Ghidra spot-checks caught FOUR decision-bearing subagent or record errors in one session. The standing "verify the crux yourself" rule paid for itself four times; verify in the SAFE direction too.
metadata:
  type: feedback
---

# 🛑 VERIFY THE CRUX YOURSELF — it caught FOUR errors in ONE session

**2026-08-06.** In a single session, the orchestrator's own byte reads and Ghidra decompiles caught
**four** decision-bearing errors — each one in a subagent report or in the standing record, each one
capable of steering a flash decision:

| # | the error | what the check found |
|---|---|---|
| 1 | **`tp+0x74a4` off-by-`0x1000`** — the **THIRD occurrence** | `tp + 0x74a4 = 0xC64A4`, byte **`0x00` on stock, V74 and V75** ⇒ Monitor 2 is **ARMED in every build**; the wrong `0xC74A4` reads `0xEA` and falsely says "gated off" |
| 2 | **DTC-map byte order reversed + an out-of-range descriptor scan** | the map at `0xB9548` gives the DTC as raw `bytes[2],[1],[0]`; the reversed read produced ids that do not exist |
| 3 | **fault_id off-by-one** | `0xC41668` is fid **80** (not 81), `0xD48394` is **72** (not 73), `0x540011` is **16** (not 17) |
| 4 | **the `0x1AB` flag described as a narrow 3-group test** | **bit10 alone covers 75 fault_ids — 40 of the 43 EPS-disabling ones** ⇒ it is a **broad fault-class indicator**, not a narrow one, and reading it as narrow would have thrown away its diagnostic value |

⇒ **the standing "verify the crux yourself" rule paid for itself four times in one session.** Keep doing
it. Every one of these was a *plausible* claim delivered with confidence; none was caught by reading the
report more carefully — all four needed an independent byte read or decompile.

## How to apply
- **Recompute, never accept, a `tp`-relative address** — and show the addition. Errors 1 and 3 are the
  same failure: an address or an index handed over instead of derived.
- **Verify in the SAFE direction too.** A *"no / don't flash"* deserves the same independent check as a
  *"go"* — a wrongly-blocked build costs a session, and error 1 runs precisely toward "this mechanism is
  dead," the direction that suppresses work.
- **Decompile first, then read the assembly** ([[feedback-decompile-first-then-assembly]]) — errors 2
  and 4 were both structure claims formed upward from bytes.
- **Byte-check with Python AND decompile with Ghidra** ([[feedback-verify-with-ghidra-and-bytes-both]]) —
  neither alone would have caught all four.

Related: [[feedback-verify-subagent-conclusions]] · [[feedback-verify-subagent-claims]] ·
[[reference-accord-monitor2-corridor-and-the-c64a4-trap]] ·
[[accord-descriptor-bit13-is-the-fault-fingerprint]]
