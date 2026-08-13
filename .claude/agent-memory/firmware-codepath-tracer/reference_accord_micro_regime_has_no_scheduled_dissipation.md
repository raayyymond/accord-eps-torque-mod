---
name: reference_accord_micro_regime_has_no_scheduled_dissipation
description: Full census of every centring/damping candidate in the micro regime (parking speed, engaged) on the CURRENT build -- all three viscous terms are gated off, leaving only a phase-advance lane, an inertia term and an anti-damping D-term. This is a coherent firmware-side account of the measured Re(Z)<0 at 6-9Hz, and it reframes the crux as a MISSING VISCOUS TERM IN THE BASE ASSIST rather than a muted centring lane. Includes a byte-read of the V96 image showing V86B's FactorC arming is NOT carried.
metadata:
  type: reference
---

# Nothing in this firmware dissipates energy in the micro regime — 2026-08-12 (`fw-return`, Q4)

Answering team-lead's *"what, if anything, still provides centring/damping while LKAS is engaged at
parking speed?"* Full writeup `analysis-2020accord/_v97/fw_return.md` §7.

## The census [EVIDENCE except where noted]

| candidate | state in the micro regime, **current build** | why |
|---|---|---|
| End-stop cushion `gp-0x6b62` | **ZERO** | gate needs `\|gp-0x6bf0\| > 8878` — see [[reference_accord_return_centre_is_an_end_stop_cushion_not_centring]]; V92 duty 0.0000 engaged |
| Base-assist damper `ch0 = (FactorC(speed)×FactorE(rate))>>10` | **ZERO** | `FactorC Y[0]=0` at `X[0]=35 km/h`; **byte-read of the V96 image this session: m26 `Y=[0,234,429,908]`, m27 `Y=[0,233,426,875]`** ⇒ V86B's `Y[0]` arming is **NOT carried on the current car** |
| comp-add `FUN_000456a4` | **ZERO** | gate needs `gp-0x6ac0` ≳ 1000 ct ≈ 212 °/s |
| r24/r26 torque-derivative lane | **LIVE, 3.000× (schedule max at creep)** | but a **+84° phase advance on TORQUE**, not a viscous (rate) term |
| `gp-0x6b26` / `0xCBE74` | **LIVE** | an **INERTIA** term — raises apparent inertia, dissipates nothing |
| `FUN_0003a382` D-term, `Kd=2.000`, unfiltered | **LIVE** | previously identified as the sole **pumping** term at 7.79 Hz |
| column friction | live, mechanical only | measured on-car to damp it (grip −0.655 vs control −0.266) |

## The conclusion that matters

**All three viscous candidates are gated off in the micro regime. What remains is a phase-advance
lane, an inertia term, and an anti-damper.** ⇒ There is **no scheduled dissipation at all** in the
regime the operator's micro-ratcheting complaint is about. That is a coherent firmware-side account
of the measured `Re(Z) < 0` at 6–9 Hz (−3480, coh² 0.804 in the micro band) without needing any
engagement-specific mechanism.

🛑 **This reframes the crux.** The engaged 7.8 Hz ring in the driver torque is not a *muted centring
lane* — the centring lane is an end-stop cushion that is dead in manual too. It is a **missing
viscous term in the base assist**, in a regime where Honda schedules none and where our own live
terms are inertia + phase advance + an unfiltered D-term.

## 🛑 But the obvious fix is already priced and refused
Re-arming the base-assist damper into the micro regime requires `FactorE Y[0]` off zero = **a step at
zero rate**, which is the **V80 "worst grinding ever"** move; and `FactorE X[0]` is **60 counts**, not
12. See `memory/accord-damper-cannot-reach-micro-regime.md`. Any V97 proposal in this direction has to
solve the step-at-zero-rate problem first, not re-discover it.

## Related
[[reference_accord_return_centre_is_an_end_stop_cushion_not_centring]] — the lane this census retires.
[[reference_accord_creep_damping_dead_rate_gain_max]] — the creep schedule this extends to the
current build (and confirms V86B's arming is not carried).
