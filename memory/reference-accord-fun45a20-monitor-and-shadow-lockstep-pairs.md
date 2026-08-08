---
name: reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs
description: "FUN_00045a20 is a previously-undocumented hard-shutdown monitor feeding DTC 0x1d; FUN_000462e6's first arg is DATA not a DTC index; and four write-both-or-fault shadow pairs on the torque chain are ruled out as V40 fault candidates."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2a888703-82cf-4378-8b23-ce6677f440d5
  modified: 2026-07-19T23:29:20.763Z
---

From an image-wide sweep (2026-07-19) of `gp-0x6ace` / `gp-0x138a` / `gp-0x6acc` / `gp-0x6b98` /
`gp-0x6b94`, every `ld.h`/`ld.hu`/`st.h` with `gp` as base across the 1 MiB image.

## NEW monitor: `FUN_00045a20` → DTC `0x1d` (hard-shutdown class)

Undocumented in this kit before now. Computes `(gp-0x6acc − gp-0x6ace) × 1/1024`, compares against a
**float** tolerance band LERP'd from `tp+0x7610..0x761c` = **`0xC6610..0xC661C`** (values `350.0`,
`410.0`, `5000.0`, `400.0` — read directly, stock and unchanged in V38/V40), keyed on `gp-0x6a10` and
sign-gated by `gp-0x6abe`. Out of band → `FUN_000462e6(0x3a09, …)`.

⚠ **`FUN_000462e6` unconditionally calls `FUN_00016de6(0x1d, param_1, 1, 1)` for every caller.** So
`0x3a09` / `0x3f8e` / `0x3f1b` are the DTC's **data argument, not the DTC index** — all three callers
feed the *same* `0x1d` hard-shutdown class. This partially closes CLAUDE.md's open
"`0x1D` ↔ `0x49` ↔ `0xF00049` mapping" question: the `0x3fxx` values were never indices.

Call order, all unconditional every cycle from `FUN_0002214a` (`w_steer_control_task`):
`0x2293a`→`FUN_0004503c` (governor) → `0x22978`→`FUN_0004595a` → `0x22984`→`FUN_000456a4`
(writes `gp-0x6acc = gp-0x6ace + comp_term`) → `0x229c2`→`FUN_00045a20`.

**Not a snap-vs-lag detector.** Because `gp-0x6acc` is written same-cycle from `gp-0x6ace + comp_term`,
the checked delta reduces to `comp_term` itself — it bounds the post-governor compensation term. So it
is **not** a mechanism by which removing the governor slew limit would trip a fault. Causal link to V40
NOT established.

## Four shadow lockstep pairs — RULED OUT as V40 fault candidates (clean negative)

Same write-both-or-fault family as the known `gp-0x4f64`/`gp-0x448a`:

| variable | shadow | guarded in | on mismatch |
|---|---|---|---|
| `gp-0x6ace` | `gp-0x4cca` | `FUN_0004503c` | `FUN_0006b9fa` → `FUN_0006ce7c(4)` |
| `gp-0x6b94` | `gp-0x4ce0` | `FUN_0003aa2c` (aggregator) | same |
| `gp-0x6acc` | `gp-0x4cc8` | `FUN_000456a4` | same |
| `gp-0x4f64` | `gp-0x448a` | `FUN_0007b022` (3 branches) | `FUN_0006b9ee` → `FUN_0006ce7c(0x17)` |

In every case **both halves are written in the same branch, same instruction sequence** — atomic w.r.t.
the check. A flat cap table or an unslewed governor changes the *value* written but cannot desync the
pair. `gp-0x448a` has zero writers outside `FUN_0007b022`. Do not re-walk these.

`gp-0x138a` (the governor accumulator) has **6 refs, all inside `FUN_0004503c`** — private state, not
externally monitored.

## Still unlocated
The actual Y-row / Q13-slope **interpolation math** feeding `FUN_0007b022`. That function receives
pre-computed candidate floats via a parameter struct and only shadow-guards/clamps them. ⚠ Consequently
the long-standing "cap X-axis = motor resolver electrical-angle rate, 7-hop verified" claim is
**UNVERIFIED** — two agents could not confirm it, and it originates from the same session that produced
the retracted CRC-gap error. See [[reference-crc-chain-is-50-blocks-c5000-not-a-gap]].
