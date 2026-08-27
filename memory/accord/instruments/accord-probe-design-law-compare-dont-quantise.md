---
name: accord-probe-design-law-compare-dont-quantise
description: "THE DESIGN LAW from all 45 probe builds V53->V97: every probe that DECIDED something was a sign bit paired with a magnitude channel, or a deliberately-designed control; every UNINTERPRETABLE null was a single threshold rung on a quantity with no measured distribution and no positive control. The fix is structural — when you don't know a signal's scale, COMPARE it, don't QUANTISE it. A comparator rung is immune to UNDER-RANGED and OVER-RANGED by construction."
metadata:
  type: feedback
---

# 🛑🛑 THE PROBE DESIGN LAW — 45 builds, one pattern

> **Every probe that DECIDED something was a SIGN BIT PAIRED WITH A MAGNITUDE CHANNEL, or a
> deliberately-designed CONTROL. Every UNINTERPRETABLE null was a SINGLE THRESHOLD RUNG on a quantity
> with no measured distribution and no positive control.**

**Why:** it explains V64, V68, V69, V72, V90, V92 and V96 as **one** failure rather than seven, and it
explains why V54, V60, V85, V88, V89 and V90's live rungs worked.

**How to apply:**
- **Never spend a rung on a bare threshold against a quantity whose distribution you have never seen.**
- **Size every field against its OWN lane's reachable output** — not a downstream clamp or a writer's
  clamp. Those are **gates** (GATE 3). V96 sized against `gp-0x6b70`'s ±8192 **clamp** and under-used
  its channel **~4×**; and its regressor was **34× over-range**, pinning `M ≡ 0` on three routes.
- ⭐ **BETTER — dissolve the sizing problem entirely: COMPARE, DON'T MEASURE.**
  > When you do not know a signal's scale, do not QUANTISE it — **COMPARE it.** A comparator rung
  > (`|A| ≥ |B|`) is **immune to UNDER-RANGED and OVER-RANGED by construction**: no LSB, no ceiling,
  > no assumed distribution. It compares at **full precision inside the cave, before quantisation
  > exists**, and its **duty is the answer.**

  Two comparators rank **three** terms per frame with **no scale assumption at all**.
  ⚠ Buildability: V96's flown cave used `r6`/`r7` only with **single-operand** rungs; a comparator is
  two-operand ⇒ **recompute the operand inside each rung** (+~20 B, keeps the proven discipline) rather
  than claim a third scratch register dead at the hook.

## 🛑 The kit usually KNEW at cut time — the knowledge was there, the GATE was not
- V73 cut to ONE rung *because* V72's five returned an uninterpretable zero.
- V75 caught its own identity-blindness **before** flight.
- **V86's docstring says outright: *"THE PROBE CANNOT SCORE `0xC40D4` IN FORCE."***
- 🛑 **V80's docstring said it could not discriminate itself from V79 at the flown speeds — and it flew
  anyway.**
⇒ **Make it a gate, not a note.** Before cutting, **write the sentence a null will license.** If the
honest answer is *"we would not be able to tell"*, **the build is not ready.**

## The endpoint arithmetic that makes short drives sufficient
A comparator duty is a **per-frame** read, not a statistical contrast: `SE(p) = sqrt(p(1−p)/n_eff)`,
`n_eff = T/τ`. At a **pessimistic τ = 1.0 s**, **T = 17.2 s ⇒ n_eff = 17**, and duties of
**0.9 / 0.5 / 0.1 separate at ~3σ**.
⇒ **17 s resolves the ORDERING of the arms — which is the endpoint. It does not resolve a duty better
than ±12 %, which is not the endpoint and must not be claimed.**
🛑 This matters because the operator **stops the moment he feels the symptom**: *"the exposure really
should not matter… I am generally going to stop instantly."* **Design for ~15–30 s, one episode.**
Endpoints needing matched episodes or cross-build contrasts are **UNBUILDABLE — do not propose them.**

Related: `[[accord-v97-flew-lever-live-null-was-ours]]` · `[[accord-observer-residual-two-arms-v89-v97]]` ·
`[[accord-v64-null-is-on-the-gate]]` · `[[accord-v68-detector-still-zero-no-positive-control]]` ·
`[[feedback-size-probe-rungs-against-lane-reachable-output]]` · `[[feedback-probe-the-gate-not-just-the-output]]`
