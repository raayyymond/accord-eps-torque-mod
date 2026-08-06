---
name: reference-accord-monitor2-corridor-and-the-c64a4-trap
description: Monitor 1/2 corridor mechanics (±5/1024, charge:leak 2:1, 10-cycle trip) plus the tp+0x74a4 = 0xC64A4 off-by-0x1000 trap that has now been made twice.
metadata:
  type: reference
---

🛑🛑 **THE `tp+0x74a4` TRAP — MADE TWICE NOW, AND IT NEARLY CLOSED THE ONLY SURVIVING CANDIDATE.**

`FUN_00043e44`'s gate at `0x44950` is `ld.bu 0x74a4[tp],r11`. With **`tp = 0xBF000`**:
```
tp + 0x74a4 = 0xC64A4     <- what the instruction reads.  Byte = 0x00 in stock/V74/V75.
0xC74A4                   <- the wrong address.  Byte = 0xEA.  A real byte, wrong one.
```
Gate condition is `== 0` ⇒ **Monitor 2 is ARMED, in every build.** A 2026-08-06 session byte-read
`0xC74A4`, concluded *"permanently gated off — dead regardless,"* and the orchestrator **relayed it after
checking the same wrong address**, because it verified the address it was handed rather than deriving it
from `tp`. A tracer caught it by re-deriving. `reference_accord_consistency_monitor_hardshutdown.md`
already records the identical slip on the identical byte from the V27 session.

> **RULE: never byte-check a tp-relative address you were handed. Recompute `tp + disp` yourself and
> show the addition.** Verifying the wrong address produces a clean-looking confirmation of a false
> claim, and it runs toward "this mechanism is dead" — the direction that suppresses work.

---

## Monitor 1 (`FUN_00042af8`, int) / Monitor 2 (`FUN_00043e44`, float) — full mechanics [EVIDENCE]

Both at **1 kHz** (sole caller `FUN_0002214a`). Both compare `gp-0x6b98` (delivered command) against an
independently re-derived value, **tolerance ±5/1024** (Monitor 1 raw int `0x43b24-0x43b48`; Monitor 2
float `0x448d6-0x448f6`, literals `0x3BA00000` / `0xBBA00000`).

| property | value |
|---|---|
| charge | **+0.001**/cycle when faulted (`0x3A83126F` @0x44966) — int twin **+10** |
| leak | **−0.0005**/cycle when clear (`0x3A03126F` @0x4498e) — int twin **−5** |
| **break-even duty** | **exactly 1/3** (`0.0015d − 0.0005 = 0` ⇒ `d = 1/3`) |
| latch trigger | accumulator ≥ **0.01** while faulted ⇒ +1024.0 ⇒ state 3 ⇒ +1024 every cycle |
| trip | accumulated word > **128.0** → `FUN_000462e6(0x3f1b,…)` → `FUN_00016de6(0x1d,…)` → DTC 0x1c/0x1d → **`0xF00049`**, hard-latched until power cycle |
| ⇒ **time to trip** | **10 consecutive faulted cycles = 10 ms** |

★ **Sign alternation does NOT cancel** — every one of the 7 flags is a bilateral `|diff| > tol` test, and
the accumulator only asks *"is any flag nonzero this cycle"*, never a signed running sum. **A relay
flipping polarity trips the same flag at either sign.**
★ **No minimum-duration gate** — a single isolated cycle charges identically to the first cycle of a
sustained burst.
★ **`gp-0x6bd0` is recomputed at 100 Hz and HELD**, so Monitor 2 sees the same value for exactly **10
consecutive cycles**. ⇒ via this lane the shortest possible plateau visit is **10 cycles = exactly the
trip threshold**, so a *dwell*-triggered rule would fire on **every entry in both builds**. It does not.

## What the corridor actually compares — and when the gap can open

```
gp-0x6b04 = rate_shaped_value                                          (PRE)
gp-0x6b98 = clamp( clamp(rate_shaped + feedforward, ±governor), ±8192 )  (POST)
fVar23    = clamp( min(governor_float(gp-0x4f64), gp-0x6b04 + gp-0x6dac), ±governor ), ±8.0
```
`gp-0x6b04` is the **pre-feed-forward / pre-governor-clamp / pre-final-clamp** snapshot of the *same*
pipeline that becomes `gp-0x6b98`. ⇒ **under non-saturating conditions they are trivially equal and the
monitor cannot fire. The gap opens ONLY when a clamp BINDS.**

That is the physical account of why a **transition** and not a **dwell** would trip it: a level clamped
for 200 ms settles into a steady, non-faulting relationship; the *moment of the step* is when the pre- and
post-clamp pipelines transiently disagree.

**The sizing that makes it plausible** [BELIEF — not numerically closed]: governor ceiling **4762**
(`0xC6202`), openpilot's own amplitude rail **4096** (= 86% of it), **16.07% of engaged time already sits
against an openpilot rail**, and a relay sign-flip injects **594 counts (V75) / 450 (V74)** on top.
**A stoplight launch with openpilot holding the lane is the maximum-demand, minimum-speed corner.**

✅ **`gp-0x6dac` is CLOSED and is NOT the path** [EVIDENCE, two methods — `search_instructions` over
183,429 instrs **and** a raw whole-1 MB LE byte scan]: exactly 1 writer / 1 reader.
`FUN_00042adc` (clamps ±10.0) ← `FUN_00027b0a` (an ~800-line driver hand-torque **sensor
redundancy/voting** subsystem) ← `FUN_0002214a`. **Structurally unreachable from the relay.**

## Still open
1. Byte-exact simulation of `fVar23` vs `gp-0x6b98` through one relay step — needs telemetry of
   aggregate-command headroom-to-clamp, or `gp-0x6afe` (feed-forward)'s producer and typical magnitude.
2. `FUN_00070a98` (DTC `0x26`, lateral-model residual, accumulators `gp-0x2880`/`gp-0x2884`) — structural
   only; **its threshold constants were NOT verified against `tp = 0xBF000`** ⇒ apply the trap rule above
   before trusting any value from it.
3. RTOS preemption between task-5 `jarl`s — dropped once `FUN_000347b8` was shown unreachable on magnitude.

See [[reference-accord-v75-fault-refutation-ledger]] and [[reference-accord-v74-v75-damper-is-a-sampled-relay]].
