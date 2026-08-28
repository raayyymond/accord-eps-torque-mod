---
name: accord-v111-flew-alpha2-is-the-only-delta
description: V111 flew 2026-08-27. alpha2 (0xC40DC 22->14) is the ONLY dynamics change from V108, so every symptom change is attributable to it - grinding mostly resolved, oscillations gone, ratcheting reduced, but max steering angular velocity and acceleration LOST. Lowering alpha2 adds phase lag which rotates the gp-0x6b26 inertia term into FRICTION, ~1.87x at manoeuvre frequencies. MAGNITUDE not yet verified.
metadata:
  node_type: memory
  type: project
---

# ★★★★★ V111 FLEW — AND α2 IS A **SINGLE-VARIABLE EXPERIMENT**

**2026-08-27.** `image 9c4865cf… / .rwd 221d99c6…`. Flown after V108.
⭐ **The cleanest attribution in this kit's history:** V111 − V108 = **three payload bytes**, of which
two are the CAN-427 telemetry tap (no dynamics) and **one is `0xC40DC` α2 22→14**. Every dynamics
cell — relay knee 600, gain 5346, the `gp-0x6b26` Y row, the biquad, the whole 164-byte cave — is
**byte-identical**. ⇒ **whatever the operator felt, α2 caused it.**

## THE OPERATOR'S REPORT — his words, the primary readout
> *"Regarding the grinding issue, **most of it has been resolved**. However, **grind number one still
> occurs at low speeds between 5 and 10 mph, particularly under strong openpilot commands**. The
> frequency is **higher-pitched than before**, but it is a **muted or attenuated version**. While
> this is great progress, we still need to work on eliminating it completely."*
>
> *"As for the oscillations, **I no longer observe general oscillations** when driving straight or
> during slight turns. **The ratcheting effect also seems reduced**, but this appears to have come at
> **the cost of maximum steering angular velocity and acceleration**."*

⇒ **THREE improvements and ONE regression, all from one byte.**

## ⭐ THE MECHANISM — LOWERING α2 ROTATES INERTIA INTO **FRICTION**
`gp-0x6b26 = −K · gp-0x6c2c` and `gp-0x6c2c` is the **filtered acceleration**
([[accord-gp6b26-is-inertia-not-damping]]). A `−K·accel` term is **pure apparent mass while it is in
phase**. Add EMA phase lag `φ` and it rotates: against velocity the term is
`K·ω·|H|·exp(−j(φ+90°))`, so the **component in phase with velocity — i.e. FRICTION — scales as
`sin φ`.** Lowering α2 roughly **doubles φ**:
```
    f Hz   |H| 22   phase 22   |H|sin   |H| 14   phase 14   |H|sin    FRICTION ratio   MASS ratio
    1.00    0.9999    -0.69     0.0120   0.9997    -1.29    0.0224       1.87x          1.000x
    5.00    0.9973    -3.43     0.0596   0.9920    -6.39    0.1104       1.85x          0.990x
    8.00    0.9931    -5.47     0.0946   0.9800   -10.13    0.1723       1.82x          0.976x
   21.73    0.9520   -14.32     0.2355   0.8758   -25.20    0.3728       1.58x          0.859x
```
⇒ **the friction-like component nearly DOUBLES at exactly the frequencies he steers at, while the
mass component barely moves (1.000× at 1 Hz).** His *"increased mass and friction"* is, by this
account, **almost entirely FRICTION** — and friction acts against velocity, which is precisely what
caps max angular velocity. ⭐ It also explains the ratchet reduction (more damping at ~8 Hz) and the
grinding reduction (−27 to −40 % over 61–300 Hz) **from the same single byte.**

## 🛑🛑 THE HOLE IN THIS EXPLANATION — STATED, NOT PAPERED OVER
**The magnitude is NOT verified, and there is a counter-argument.**
- `gp-0x6b26` **clamps at ±511** against a residual clamped at **±20,000** ⇒ the whole term is at most
  **2.6 %** of the residual range, and one memory records its engaged **p50 at 4.8 counts**.
  **Doubling 11 % of a 2.6 % term is a very small number to explain a felt loss of steering rate.**
- ⚠ **AND THE COUNTER-ARGUMENT:** lowering α2 also **shrinks `|gp-0x6c2c|`**, which should make
  `gp-0x6b26` **rail LESS often** — and a railed acceleration term is the Coulomb-relay drag that
  [[accord-gp6b26-is-a-61hz-bandpass-and-v107-railed-it]] blames for lost steering rate. **That
  points the opposite way.**
⇒ **[BELIEF, right sign and right band, magnitude UNVERIFIED.]** Do not present this as settled.

## ✅ WHAT WOULD SETTLE IT — AND THE DATA MAY ALREADY EXIST
**Route `21` is on disk: 18 segments, uncached, newer than route `1e` (V107).** If it is the V111
drive it carries **V111's own tap on `gp-0x6abc`** plus the standard channels, which gives:
1. the **relay input amplitude** V111 was built to measure (decides whether the knee is a lever at
   all — GATE 2 says it only bites below ~200–400 counts); and
2. `gp-0x6b26`'s **actual engaged magnitude and rail duty**, which settles the hole above.
🛑 **It needs registering in the `ROUTES` table used by `extract_r7d.extract_route()` before it can be
extracted.** That is the single highest-value action available.

## 🛑 THE DIRECTIVE THIS PRODUCED
[[feedback-do-not-buy-ratchet-with-mass-and-friction]] — **do not buy the ratchet with mass or
friction.** Whatever α2's magnitude turns out to be, the operator has ruled out this whole class of
fix, and that reframes the lever search onto the **torque-sensor path**.

## ⚠ THE UNCOMFORTABLE COROLLARY
**A straight α2 revert (14 → 22) gives back a measured win.** It would recover the steering rate but
lose *"most of the grinding has been resolved"* and *"no oscillations"* — **three improvements for
one regression.** A single EMA pole **couples** the magnitude cut (which helps) to the phase lag
(which hurts), so the revert is a trade, not a fix. **Do not propose it as an obvious win.**

Related: [[accord-c40dc-is-the-band-limit-lever]] · [[accord-kd-is-one-knot-of-a-flat-lerp]]

## 🛑🛑 CORRECTION 2026-08-27 (later) — THE α2 STORY DOES **NOT** EXPLAIN THE LOST STEERING RATE
The mechanism above (*"EMA lag rotates the inertia term into friction, and friction is what caps
angular velocity"*) is **arithmetically right about the rotation and WRONG about the consequence.**
**The rate deficit was then measured across 18 routes and it PREDATES V111 on every build:**
`achieved/demanded` at 60+ °/s is **0.09–0.49, median ~0.26**, and **route 21 (V111) = 0.24 — dead
typical.** A deficit present on every build cannot have been caused by a byte that changed on one.
⊕ And the term is far too small: `gp-0x6b26` is clamped by `cal(0xC407E) = 511` (decompile-confirmed
in `FUN_00036c12`, operand `tp+0x507E`) ⇒ ≤ 2.6 % of the ±20 000 residual, and α2 moves only its
**friction component** (Δ(|H|·sinφ) ≈ 0.078 at 8 Hz) ⇒ **≤ ~40 counts ≈ 0.2 % of range.**
🛑 **⇒ THE α2 REVERT IS RETIRED AS A RATE FIX.** It may still explain a change in *feel*; it does not
explain the rate ceiling. Full working: [[accord-the-rate-deficit-is-real-universal-and-not-v111]].
