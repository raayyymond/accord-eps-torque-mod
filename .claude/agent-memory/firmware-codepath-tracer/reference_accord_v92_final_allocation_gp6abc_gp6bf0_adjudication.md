---
name: reference_accord_v92_final_allocation_gp6abc_gp6bf0_adjudication
description: V92 = V91's 0xCBE74 x1.5 dose (operator's decision to fly despite the sizing concerns) + a re-specced telemetry cave. Adjudicated a cross-agent claim myself and found a real nuance -- gp-0x6bf0 is NOT inside the return-centre functions (FUN_00036388/FUN_000360fe), it's in a separate function (FUN_0003bd7c) with 15+ readers including the shaper. gp-0x6abc IS confirmed raw/unfiltered motor rate. Final 7-bit allocation fits entirely in 0x14A, T=15 for the dose-in-force threshold rung, ~106B cave estimate.
metadata:
  type: reference
---

# V92 telemetry — conflicts adjudicated, final allocation (2026-08-11)

Operator decision: fly V91's `0xCBE74` ×1.5 dose regardless of the five reasons it's underpowered
(logged this session) — "we are flying regardless, so the instrument is free." V91 stays frozen on disk
as the cal-only variant; V92 = V91's 12 bytes + this cave.

## Adjudicated a cross-agent claim myself (not deferred) — one confirmed, one corrected

A parallel trace claimed return-centre (`gp-0x6b62`) is the sum of two differently-signed terms, Term 1
`=-sign(gp-0x6abc)` and Term 2 `=-sign(gp-0x6bf0)`.

**Confirmed independently**: `gp-0x6abc` IS raw, unfiltered motor rate — its producer `FUN_00041464`
(already fully traced this session for `gp-0x6c2c`) assigns it directly from `gp-0x4f50` with no EMA in
the normal-operation branch (distinct from `gp-0x6abe`, the filtered arm, already established this
session too). Decompiled `FUN_000360fe` (return-centre's magnitude producer) fresh: `gp-0x6b64 =
-(LERP(gp-0x6bda)·gp-0x6abc/scale)` — Term 1's structural form matches `-sign(gp-0x6abc)` exactly,
provided the LERP output stays non-negative (not independently re-verified the Y-table this session).

**Corrected**: `gp-0x6bf0` is NOT referenced anywhere inside `FUN_00036388` or `FUN_000360fe` — full
disassembly of both (already done this session) shows zero hits. It's computed in a separate, large
function `FUN_0003bd7c` (torque-margin/diagnostic-flavored, gated by LKAS engage-state `gp-0x67fe`), and
**has 15+ readers across many functions, including the shaper `FUN_00042af8` directly** — a real, live,
heavily-consumed signal, just not literally a summand of `gp-0x6b62` the way "same lane, two terms"
implied. (Its derivative `gp-0x6bee` = `gp-0x6bf0 + sVar13`, by contrast, has ZERO readers anywhere —
dead diagnostic tap.) **The proposed two-sign-bit rung survives this correction** — it only needs both
signals to be real and their joint sign genuinely unresolved from statics, which holds regardless of
which function sums them.

## Final allocation, all 7 of `0x14A`'s free bits, `0x18F` untouched

| bit | signal |
|---|---|
| 427 (50Hz) | `\|gp-0x6bbe\|` (boost magnitude — the top anti-damper candidate per this session's aggregator enumeration) |
| b7 | `sign(gp-0x6bbe)` |
| b6 (unchanged) | `\|gp-0x6bf6\|≥512` (K1/observer, kept free, no reason to spend budget disturbing it) |
| b5 (unchanged) | `gp-0x6ae2≠0` (K1/observer friction relay) |
| b4 (reclaimed) | `sign(gp-0x6abc)` |
| new byte7 bit | `sign(gp-0x6bf0)` |
| new byte7 bit | `\|gp-0x6b26\|≥15` — **dose-in-force for V91's cal edit**, cave-based (427 moved away from `gp-0x6b26`) |
| b3 (unchanged) | fingerprint≡1 |

`T=15` chosen from log-linear interpolation across route 77's real percentiles (p50 5.5/p95 58.3/p99
114.3/p99.9 184.7/max 319.1, all scaling ×1.5 exactly under the dose): duty(stock)=0.242,
duty(×1.5)=0.339 — both comfortably off 0/1, clean +0.096 shift.

**Cave-size estimate: ~106 bytes** (V90's 5 rung shapes keep their byte cost, just repointed; +2 new
rungs ~8-10B each; +a new `byte7` RMW epilogue ~14B, `byte7` never written before; the 427 packer edit
is a 2-byte halfword change, not cave bytes) **against 1138 bytes free** in the cave extent.

Also this session: governor-ceiling (`gp-0x4f64`) mechanism for return-centre DROPPED (measured on 4
routes, doesn't bind by 8.3×, taken as given from the source trace, not re-derived); rate-channel rule
corrected and scoped — `0x14A`'s `rate_c` for absolute-magnitude questions, `0x18F`'s `rate_f` only for
phase/impedance work (the two channels read ~24% apart in magnitude, confirmed by the source trace).

Full write-up: `docs/SPEC-2026-08-11-telemetry-budget.md`, ADDENDUM 2.

Related: [[reference_accord_vehicle_bus_clearance_and_aggregator_probe_reaim_2026-08-11]] (the prior
round this supersedes for the winner-set specifics, though the vehicle-bus clearance verdict stands).

## FINAL ROUND — K1/observer question closed, b5/b6 reallocated, spec complete

Measured on-car: `(b6,b5)` 2×2 gives `P(b5|b6=1)`=0.986→1.000 above 1°/s (discriminating cell 0.63% of
engaged frames) — friction and `|model|` near-collinear exactly where the operator names the symptom, a
STRUCTURAL explanation for V89's null, not a pending measurement. `b5`/`b6` freed for reallocation.

**Final 4-bit pick** (from 6 candidates, `sign(gp-0x6bbe)` already placed on `b7`): `sign(gp-0x6b62)` +
`gp-0x6b62≠0` (three-state disambiguation, needed because of confirmed disable branches) + `sign(gp-0x6abc)`
(convention anchor) + `sign(gp-0x6bf0)` (the second unresolved signal). **Dwell-snap-state and
`gp-0x6bda` excluded** — the former per an explicit instruction not to spec its semantics until a
cross-agent polarity disagreement resolves (I independently re-derived the increment condition as
`|gp-0x6b64| < cal(0xC618A)=1024` from my own full decompile of `FUN_00036388`, offered as one input to
that adjudication, not used to override the hold).

**No second `0x18F` hook needed** — everything fits in `0x14A`'s existing capacity (reallocated `b5`/`b6`
+ 2 new `byte7` bits). **Identity simplified**: any single frame with `0x14A` byte7[7:6] nonzero proves
this build — no prior build in the lineage has ever written there, a fresh capacity claim disjoint by
construction, not dependent on any prior build's measured duty.

Full final spec: `docs/SPEC-2026-08-11-telemetry-budget.md`, ADDENDUM 3. Session's telemetry-budget work
complete per team-lead's close-out instruction.

## TWO VARIANTS spec'd, contingent on the pending dwell-relay polarity adjudication

Team-lead asked for a conditional Variant B (slot 4 swaps `sign(gp-0x6bf0)` → the dwell-relay snap
state `gp-0x6a82 > cal(0xC627E)=20`, IF the polarity adjudication confirms `<`), reasoning that
`sign(gp-0x6b62)` "subsumes" `gp-0x6bf0`'s contribution so the diagnostic bit is worth less than a
mechanism test. **Flagged one nuance**: that "subsumes" framing rests on the ORIGINAL "two terms of one
lane" model — my own earlier correction this session found `gp-0x6bf0` is NOT literally inside
`gp-0x6b62`'s sum (it reaches the assist chain via the shaper, independently). The swap's conclusion
still holds on its own separate, sufficient merits (a relay/detent test is a different hypothesis class
than 4 linear sign-correlation bits) — flagged the imprecise wording, not the conclusion.

Both variants fully spec'd in `docs/SPEC-2026-08-11-telemetry-budget.md`; only slot 4 differs. Duty
bracket for the snap-state bit stated as genuinely wide/unpredictable, with both rails (always-on,
never-on) argued as independently informative, not assumed favorable.

## CLOSED — polarity confirmed `<`, Variant B is the final shipped spec

Four independent sources converged on `<` (a fresh decompile reading Ghidra's own p-code booleans, an
independent asm control-flow trace, three predating sessions, and a physical-plausibility check). My
own earlier `<` finding (from this session's own decompile of `FUN_00036388`) was part of that
convergence; a `>` in one of my own summary lines was a transcription slip, not a second reading.

**Physical reading, final**: `gp-0x6b64` is rate-proportional (∝ raw motor rate `gp-0x6abc`) — the
dwell arms at near-zero wheel rate, snaps to a fixed 1024-count opposing torque after 20ms of stillness,
releases when rate grows. A detent, matching "micro-ratcheting when spinning the wheel at all."
**Arithmetic caution carried into the reading**: at 7.79Hz each zero-crossing gives only ~8ms of
near-zero signal against the 20ms arm requirement, so the detent likely cannot arm during SUSTAINED
ratcheting — better read as an INITIATOR of stick-slip than a sustainer, meaning a low measured duty is
not automatically a null.

**Final 8-channel payload** (427 + 7 bits of `0x14A`): `\|gp-0x6bbe\|`(427) / `sign(gp-0x6bbe)`(b7) /
`sign(gp-0x6b62)`(b6) / `gp-0x6b62≠0`(b5) / `sign(gp-0x6abc)`(b4) / `gp-0x6a82>cal(0xC627E)=20`(new
byte7 bit) / `\|gp-0x6b26\|≥15`(new byte7 bit, dose-in-force) / fingerprint≡1(b3). One CAN hook, GATE 1
clean, identity = byte7[7:6] nonzero, cave ~106B/1138B free. **SPEC ONLY, handed off, session's
telemetry-budget task fully closed.**

## RE-OPENED — `gp-0x6bda` gates the LERP feeding `gp-0x6b64` to ZERO outside `[-397,384]`

Builder paused. Team-lead found (and I independently verified fresh via `read_memory(0xC6958,32)`,
byte-exact match, not taken on faith): the 5-point LERP feeding `gp-0x6b64` (`n=5,
X=[-397,-192,140,294,384], Y=[0,2560,2560,717,0]`) is **zero outside `[-397,384]`** — so
`\|gp-0x6b64\|<1024` (the dwell-snap arm condition) fires for TWO physically different reasons: genuine
low rate (a real detent) OR the outer gate simply being shut (`gp-0x6bda` out of window → `gp-0x6b64≡0`
→ trivially `<1024` → flat `-1024` bias, not a relay). **The snap-state bit alone cannot tell these
apart.**

**Decision made (mine, argued, not just enumerated)**: stay on ONE `0x14A` hook rather than take a
second on `0x18F`. Swap out `sign(gp-0x6abc)` and `sign(gp-0x6bf0)` for `gp-0x6bda`-in-window
(`[-397,384]`), pairing it with the existing snap-state bit as a self-validating 2×2 (`(0,0)` should
never occur — a free correctness check, same class as `b3≡1`). **Reasoning**: the two dropped bits
serve future-session value (the convention anchor, the attribution bit), not this build's two decisive
questions (net lane sign; genuine detent vs. artifact) — and a second, never-flown hook is a distinct
risk class from more bits on `0x14A`'s 10-flight-proven one, exactly the "novel cave/hook combination"
class this kit's three bricks (V24/V27/V48B) came from.

`gp-0x6bda` GATE-1 closed fresh: sole writer `FUN_00036022`, 7 real reader functions incl.
`FUN_000360fe` (this LERP) and `FUN_0003a382` (the PID's own authority-ramp index) — same zero-blast-
radius class as everything else.

Full write-up: `docs/SPEC-2026-08-11-telemetry-budget.md`. Awaiting team-lead's call on the hook
question before this is truly final.
