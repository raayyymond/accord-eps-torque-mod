---
name: accord-the-7to9hz-energy-is-manufactured-not-commanded
description: "On oscillating windows the LKAS command's 6-9 Hz power relative to its own 0.5-3 Hz power is 0.00528, while the wheel response's is 0.13962 - the response carries 26.5x more relative 7-9 Hz content than the command. Coherence is above chance (0.488 vs 0.356 shuffled, CI [0.082, 0.250]) but modest, so the command MODULATES the oscillation without CONTAINING it. The energy is generated inside the loop, not commanded, which means the oscillation is not an inherent price of 6x torque and can in principle be reduced without giving up torque. This is the missing link in V121's rationale."
metadata:
  node_type: memory
  type: reference
---

# ✅⭐ THE 7-9 Hz ENERGY IS **MANUFACTURED**, NOT COMMANDED

## [EVIDENCE] 16 routes, oscillating windows only, route-level bootstrap
Band power at 6-9 Hz expressed as a fraction of each signal's **own** 0.5-3 Hz power, so the
comparison is scale-free and does not depend on command units:
```
   median COMMAND  6-9 / 0.5-3  =  0.00528
   median RESPONSE 6-9 / 0.5-3  =  0.13962
   => the response carries 26.5x more RELATIVE 6-9 Hz content than the command

   coherence(command, rate) at 6-9 Hz = 0.488   shuffled control 0.356
   difference 0.132   route-bootstrap CI [0.082, 0.250]   -- excludes 0
```
✅ **The command is comparatively clean at 6-9 Hz; the response is not.** ⇒ **the energy at the
resonance is GENERATED INSIDE THE LOOP, not delivered by openpilot.**
⊕ Consistent by construction with [[reference-accord-lkas-lane-is-a-lowpass]] — a ~1-5 Hz low-pass
**cannot** command 7.8 Hz — and this is the first direct measurement of it rather than an inference.
⭐ **The coherence result sharpens it**: above chance, so the command **modulates** the oscillation;
but only 0.488 with 26.5× less relative content, so it does **not contain** it. **That is the
signature of a NONLINEARITY converting a low-frequency drive into energy at the resonance** — which
is exactly what [[accord-the-7to9hz-mode-is-nonlinearly-excited-harmonics]] found independently via
harmonics at 2f0/3f0.
⚠ Two routes (`ra4`, `r1e`) show command ratios of 2.20 and 1.06 against ~0.005 elsewhere, 200-400×
the rest, together with the highest coherences (0.946, 0.926). **They are outliers of a different
kind** — likely a different command channel or a saturated one. The **median** is used throughout and
is robust to them, but they should not be pooled naively in any follow-up.

## ⭐⭐ WHY THIS MATTERS TO THE OPERATOR, AND IT IS THE HOPEFUL RESULT
[[accord-the-78hz-mode-does-not-move-with-firmware-gain]] establishes the mode is a **fixed
mechanical resonance** — firmware cannot move it, and [[accord-the-damping-route-is-closed-by-the-rail]]
shows it cannot be damped further. That left only *"excite it less"*, and the obvious worry was that
excitation is simply **proportional to the 6× torque**, making the operator's two goals
irreconcilable.
✅ **This measurement says otherwise.** The 7-9 Hz energy is **not in the command**, so it is **not an
inherent price of 6× torque** — it is manufactured by a nonlinear element in the firmware's own
observer path. ⇒ **reducing the generator can reduce the oscillation WITHOUT reducing torque.**
**This is the first structural reason to think the operator's two stated goals are compatible.**

## ⇒ STATUS CHANGE FOR V121
V121 softens exactly that generator (relay knee 1800→3000) **while holding the small-signal gain
exactly at V112's.** Its rationale was **[BELIEF]** on a monotone-but-not-significant knee trend
(ρ −0.291, p 0.257) whose one simulation failed to reproduce it.
✅ **Upgraded: the PREMISE — that the energy is generated downstream of the command and therefore
attackable without spending torque — is now [EVIDENCE].**
🛑 **What is still BELIEF: that the COULOMB RELAY specifically is the generator.** The chain is
coherent (harmonics ⇒ hard nonlinearity; the relay is the signum in that path) but no measurement
isolates the relay from any other nonlinearity in the loop. **V121's effect remains UNKNOWN and the
pre-registered card stands as written.**
Tool: `rlog-tools/studies/peakturn/command_vs_response_spectrum.py`.
