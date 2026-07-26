---
name: reference-accord-v48b-repoint-asymmetry-review
description: Adversarial pre-flash review of V48B's 7-site gp-0x4f60->gp-0x1500 repoint for raw-vs-filtered lockstep/shadow-monitor asymmetry (the "V27 asymmetry" brick class) — verdict SAFE with one open item.
metadata:
  type: reference
---

2026-07-21 review, stock `code.bin`, GhidraMCP only. Traced whether V48B's 7 repointed carrier
reads (raw `gp-0x4f60` -> filtered `gp-0x1500`) create a raw-vs-filtered divergence at any
lockstep/shadow monitor. All 7 repoint sites independently reconfirmed via `search_instructions`
exact-match counts (== the build brief's list, no extra physical `ld.h -0x4f60[gp]` sites hiding
behind decompiler register-reuse artifacts): `FUN_0002c478`@0x2c480(1), `FUN_000352b4`@0x354d2/0x35aa4(2),
`FUN_0003a382`@0x3a6ca/0x3a7ca(2), `FUN_0003b49a`@0x3b4a8(1), `FUN_0003b66a`@0x3b672(1).

**Q1 — type-8 lockstep `FUN_00027b0a` (0x27b0a-0x28d21, called once at `FUN_0002214a`@0x22638) — SAFE, matched.**
Zero raw `gp-0x4f60` reads anywhere in the function (corroborated 2 ways: full `disassemble_function`
read AND `search_instructions operand_pattern=4f60 function=FUN_00027b0a` -> 0/1569, `truncated:false`).
Its "independent recomputation" walks a shared 11-lane per-channel array block (`gp-0x61a0..-0x633c`)
written EXCLUSIVELY by `FUN_00025c32` ("distribute_clamp", 10 callers, none of which is `FUN_0002c478`).
Traced the real mechanism: `FUN_0002caa2` (called immediately after `FUN_0002c478` in
`FUN_0002214a`, @0x22438) reads `sStack_1c = *(gp-0x6b12)` (the type-8 carrier's own filtered-path
output), rate-limit-checks it, and passes it inside a `{lane_idx=8, mode, ..., value=sStack_1c, ...}`
struct to `FUN_00025c32`, which is what actually populates the lane-8 slot in the shared array that
`FUN_00027b0a` later sums. **Both sides of the lockstep compare (`gp-0x6b4a`/`gp-0x6b4c`, the mixer
`FUN_00026c80` sums, vs the per-lane recompute) trace back to the SAME single filtered read** —
textbook matched/safe, not the V27 asymmetry pattern.

**Q2 — the other 4 repointed lanes' outputs — SAFE, no cross-function raw/filtered comparator found.**
- `gp-0x6b86` (`FUN_000352b4`): has its own internal shadow-pair check (`gp-0x6b86` vs `gp-0x4cde`,
  `FUN_0006b9fa` on mismatch) gated by a RAW-range plausibility test — but that raw read is one of the
  function's own 2 (repointed) loads, so self-consistent post-V48B. Sole external reader = aggregator
  `FUN_0003aa2c` (confirmed 0 raw `-0x4f60` reads there), plain `ld.h`, no comparator.
- `gp-0x6ad4` (`FUN_0003a382`): reconfirms prior memory — pure leaf (0 `jarl`), only external reader is
  the aggregator (no raw read).
- `gp-0x6b2a -> FUN_00037fe6 -> gp-0x6ad6 -> FUN_0003a382`: `FUN_00037fe6` has 0 raw `-0x4f60` reads
  (confirmed) — clean intermediate stage, no asymmetry risk.
- `gp-0x6ba6`/`gp-0x6b9a` (`FUN_0003b66a`) -> **`FUN_00034350`(the damper)/`FUN_00034a72`(boost) EACH
  have their OWN independent raw `gp-0x4f60` read** (0x34392, 0x34ace resp.) feeding a first-order EMA
  used as a FALLBACK input, muxed against the (V48B-filtered) `gp-0x6ba6`/`gp-0x6b9a` via a cal-byte
  flag `tp+0x7498`/`tp+0x7499`. **Read both flag bytes: `0xC6498=1`, `0xC6499=1` in stock** — i.e. stock
  firmware SELECTS the filtered `gp-0x6ba6`/`gp-0x6b9a` path directly; the raw-EMA fallback branch is
  not taken. All `FUN_0006b9fa` calls inside both functions are RAM-integrity self-consistency checks
  (a function's own output written to two redundant copies, checked that they still agreed before this
  cycle's write) — orthogonal to raw-vs-filtered, would only fire on genuine memory corruption. No
  comparator ties the dormant raw-EMA path to the filtered path for a DTC trip. **Efficacy note (not a
  safety issue): if a future build ever flips `0xC6498`/`0xC6499` to 0, the raw fallback activates and
  would dilute the notch's effect on the damper/boost lanes — V48B does not touch these bytes.**

**Q3 — hard-shutdown monitors `FUN_00042af8`(DTC 0x1c) / `FUN_00043e44`(DTC 0x1d) — mostly SAFE, one open item.**
Both monitors DO read raw `gp-0x4f60` once each (0x42c20, 0x43eda) — NOT among the 7 repointed sites,
correctly left raw. `FUN_00043e44`@0x43eda reconfirms prior memory: a `±25.0` plausibility
sanitize-to-range check on the raw sensor, unrelated to the function's real int/float lockstep trip
(which per prior memory compares the shaper's own int result against its own float mirror re-derivation
— never touches `gp-0x4f60`, `gp-0x69ae`, or `0xC646C` at the compare point). SAFE, matches Q3's
envelope-check hypothesis exactly.

`FUN_00042af8` is more interesting: at 0x42c1x-0x42c62 it builds `iVar45 = clamp(raw_gp4f60_rangechecked
+ [cal-gated] gp-0x6b4a_rangechecked, ±0x6400)`, storing the raw-only term to `gp-0x6af8` and the
combined sum to `gp-0x6afa` (cal gate = `tp+0x74cb`/abs `0xC64CB`). **This intentionally SUMS raw driver
torque with the type-8 mixer output `gp-0x6b4a`** (itself downstream of the same single filtered read
per Q1) — this is NOT the V27-class "two independent recomputations compared for equality" pattern;
it's a deliberate combined-signal input to corridor-arm construction. Traced `gp-0x6af8`'s 7 downstream
readers (0x43564-0x43846): they feed a multi-cycle DEBOUNCE/HYSTERESIS state machine (state vars
`gp-0x3560/61`, `gp-0x355d/e`, `gp-0x6785/86`, `gp-0x6710/11`, `gp-0x6962`, `gp-0x6a72/74`, sentinel
`0x8000`=invalid/reset) that selects THRESHOLD-CROSSING regimes — not an instantaneous bit-exact
compare-and-trip. No `FUN_0004613e`/`FUN_00016de6`/`FUN_0006b9ee` call was found gated directly by this
term in the traced window. **OPEN ITEM (not resolved statically, flagged rather than guessed):** did not
trace how far downstream this debounced state ultimately sets the corridor arm's final width fed into
the known integrator wind-up compare (`gp-0x3564`/`FUN_00016de6(0x1c)`) documented elsewhere, nor
confirm whether the notch's ~8dB/21Hz attenuation on the diluted (multi-lane) `gp-0x6b4a` term could
ever flip a threshold-crossing state near a boundary. `FUN_00042af8` is ~1769 instructions and too large
for one `decompile_function` call (hits the tool's token cap) — would need a segment-by-segment pass
(as done here for 0x43560-0x438a0) continuing past 0x438e8 to close this out fully.

**Overall verdict for the reviewed risk:** no asymmetric raw-vs-filtered divergence trip found at any of
the 7 repoint sites' immediate consumers, including the two hard-shutdown monitors' plausibility checks.
The one unresolved thread is downstream-of-downstream in `FUN_00042af8`'s corridor arm, and it is a
DEBOUNCED regime-selector rather than a hard compare, which lowers its risk profile — but it was not
traced to its terminal compare, so it should not be marked closed.

## Related
[[reference-accord-v48b-monitor1-dtc1c-notch-safety-closed]] — closes the FUN_00042af8 open item above.
[[reference-accord-v50-gp4f60-repoint-asymmetry-carryover-and-completeness-gap]] — 2026-07-23 re-verification
for V50 (same hook/repoint topology, different filter math) plus 3 newly-found readers this review's
scans missed.
