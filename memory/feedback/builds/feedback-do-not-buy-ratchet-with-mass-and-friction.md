---
name: feedback-do-not-buy-ratchet-with-mass-and-friction
description: Standing operator directive 2026-08-27 after the V111 drive - reducing ratcheting by RAISING apparent steering mass or friction is NOT an acceptable fix if it costs max steering angular velocity or acceleration. He wants BOTH low apparent mass/friction to LKAS AND no ratcheting. That makes the ratchet lever a PATH-SELECTIVE problem, not a global-impedance one.
metadata:
  node_type: memory
  type: feedback
---

# 🛑🛑 DO NOT BUY THE RATCHET WITH MASS OR FRICTION — standing operator directive

**2026-08-27, after driving V111.** In his own words:

> *"The ratcheting effect also seems reduced, but this appears to have come at the cost of maximum
> steering angular velocity and acceleration. It feels as though the current fix increases the
> steering column's apparent mass and friction. While I am fine with a change in driving feel, this
> increased mass and friction limits the maximum steering angular velocity and acceleration we can
> achieve with the lane-keep command from openpilot. **Increasing mass and friction should not be our
> primary approach to resolving the ratcheting if it comes at the cost of max steering angular
> velocity and acceleration. We want both: low apparent steering mass and friction to LKAS AND no
> ratcheting (feedback from driver torque sensor).**"*

## WHY THIS IS A DESIGN CONSTRAINT, NOT A PREFERENCE
It rules out an entire class of lever the kit has been drawn to for sixty builds. **Every
"add damping / add inertia / raise friction" fix is now off the table** unless it can be shown not to
load the LKAS path.

⭐ **AND IT IS WELL-POSED, because the two requirements live on DIFFERENT PATHS:**

| path | fed by | what it does | effect on max angular velocity |
|---|---|---|---|
| **MOTION-fed** — `gp-0x6b26` (inertia), `gp-0x6bbe` (viscous), base-assist damper | motor rate / acceleration | opposes **all** motion, whatever caused it | 🛑 **DIRECTLY CAPS IT** |
| **TORQUE-fed** — the PID in `FUN_0003a382` (P/I/D on `gp-0x4f60` − bias), the observer/friction lane | driver torque sensor | closes the assist loop the operator calls *"feedback from driver torque sensor"* | **does not load the LKAS path** |

⇒ 🛑 **A motion-fed lever cannot satisfy him by construction** — it is an output-side impedance and
the LKAS command has to push through it. **The ratchet lever must be TORQUE-PATH.**
⊕ His own parenthetical — *"ratcheting (feedback from driver torque sensor)"* — names the path. It
agrees with the kit's measurement that the ratchet is in the **bar and the angle-rate but NOT in
openpilot's command** ([[accord-ratchet-characterised-on-route-4f]]) and is a lightly-damped
closed-loop resonance ([[accord-ratchet-is-a-lightly-damped-resonance]]).

## 🛑 WHAT THIS RETIRES
- **Raising `gp-0x6b26`** (V106's ×3.0, V107's reshape) — motion-fed apparent inertia. **Any further
  dose is now against the directive.**
- **Lowering `0xC40DC` (α2) for its damping side effect** — see below; it adds friction by phase lag.
- **Raising the relay knee `0xC40BC`** — ⚠ by the verified polarity
  ([[accord-friction-polarity-more-assist]]) *more modelled friction = MORE assist*, so raising the
  knee **reduces friction compensation and therefore feels HEAVIER**. **That is the wrong direction
  for this directive**, and it inverts the reasoning in
  [[accord-the-coulomb-relay-is-located-c40bc-is-its-knee]] — which priced the knee as a ratchet
  trade **without** the mass/friction constraint in view. **Re-read that note against this one.**

## ✅ WHAT IT LEAVES
Torque-path attenuation at the ratchet frequency. The concrete candidate is **`Kd`**, the derivative
on the driver-torque error — **all four knots `0xC6AE6/E8/EA/EC` (flat 2048)**, never one
([[accord-kd-is-one-knot-of-a-flat-lerp]]). It **PUMPS at 7.79 Hz** and cutting it reduces a
**feedback gain**, not an impedance ⇒ **it cannot add apparent mass to the LKAS path.**
⚠ Its priced cost is **2.9–4.4:1 against**, paid in 18–31 Hz grinding damping. **That cost was
computed when grinding was the top complaint. It no longer is** — see the V111 report — so the trade
must be re-weighed rather than re-quoted.

Related: [[accord-v111-flew-alpha2-is-the-only-delta]] · [[accord-4x-lkas-gain-is-the-frozen-variable]]
