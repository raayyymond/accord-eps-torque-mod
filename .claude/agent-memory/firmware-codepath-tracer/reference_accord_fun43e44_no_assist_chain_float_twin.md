---
name: reference-accord-fun43e44-no-assist-chain-float-twin
description: FUN_00043e44 (the int/float lockstep monitor) never reads gp-0x6b94, gp-0x6ad4, or any individual aggregator lane — only int-converts gp-0x6acc/gp-0x6b98 and independently re-derives the corridor/boost WALL, not the assist aggregate. One unresolved float input (gp-0x6dac) in the weight-32 flag.
metadata:
  type: reference
---

`FUN_00043e44` (the shaper's float monitor twin, `0x43e44-0x449fc`) is the only int/float lockstep
function found operating in the soft-EME shaper's neighborhood. Full-function scan for this session's
question ("does an independent float re-derivation of the assist/aggregator chain exist"):

**[VERIFIED] No independent float aggregation exists.** `gp-0x6acc` (post-governor command) and
`gp-0x6b98` (final FOC demand) — both downstream-inclusive of every aggregator lane — are read via
`ld.h`+`cvtf.ws`, i.e. INT-READ-THEN-CONVERTED, never independently recomputed. `gp-0x6b94` (raw
aggregate) and every individual aggregator lane (`gp-0x6bbe` boost, `gp-0x6bd0` damping/FUN_00034350,
`gp-0x6b26` friction, `gp-0x6ad4` resonance/FUN_0003a382, `gp-0x6b62` return-to-centre, `gp-0x6b86`/
`gp-0x69a4` magnitude, inline r24/r26) do not appear anywhere in this function. Same for `gp-0x6bf0`
(driver-assist magnitude) — read twice, both int-converted, no independent float re-derivation.

**What FUN_00043e44 DOES independently re-derive: the corridor/boost WALL**, via its own float LERP
tables (`tp+0x75d4`, `tp+0x7648-0x767c`, `tp+0x7594-0x75c4` — genuine `*(float*)` RAM reads, not
conversions) and persisted float lag states `gp-0x3554`/`gp-0x3558` (`state += (target-state)*gain`,
gain from `tp+0x7418`). This is the already-known wall lockstep (int `gp-0x6af6` vs this float side,
±5/1024 tolerance) — a different subsystem from the assist aggregator.

**Consequence:** a dynamics change (e.g. adding a lag) to any single aggregator lane cannot open an
int/float divergence here, because there is only ONE computation of the assist/aggregate quantity in
this firmware (the integer one) — the float side never redoes that math, so there's no second path to
fall out of step with. This generalizes the "raising a clamp translates both sides" argument to dynamics
changes too, not just magnitude changes.

**Seven weighted fault flags** (1/2/4/8/16/32/64, sum vs threshold 128, ~10-cycle dwell,
`FUN_000462e6(0x3f1b,...)` on trip) are built from wall-tolerance / rate / authority-window checks — none
reference an aggregator lane directly except transitively through `gp-0x6acc`/`gp-0x6b98`.

**[OPEN] `gp-0x6dac`** — one input to the weight-32 flag (`fVar23` in decompile terms), traced to
concrete addresses `0x4486e-0x448d6`: `fVar23 = clamp(gated(gp-0x4f64 governor) + gp-0x6dac_gated +
mode-selected(gp-0x6b04 OR gp-0x6acc-rooted SM2/SM3 consensus), floor, 9.0)`. Two of three summands
confirmed int-converted. `gp-0x6dac` itself is read via `ld.w` as a genuine persisted float (not a
same-cycle `cvtf`), gated to roughly ±10.0. **Producer not found** — checked `FUN_00043e44` itself (no
write anywhere in the function), the governor `FUN_0004503c` (pure fixed-point, doesn't touch it), and
`FUN_00037fe6` (the `gp-0x6ad6` feedforward-torque-model producer — also pure fixed-point, doesn't touch
it). Whoever writes `gp-0x6dac` is still unresolved; Ghidra doesn't resolve gp-relative xrefs in this
project so this needs r2 or another decompile guess. Structural read (clamp-to-ceiling, narrow ±10 gate)
favors it being another wall/bound-adjacent quantity, not an independent torque prediction, but this is
not proven.
