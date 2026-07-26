---
name: reference-accord-collocation-motor-rate-damper-dead
description: "The 21 Hz vibration is a two-inertia torsional mode; the firmware's motor-resolver-rate damper is NON-COLLOCATED with the wheel-side mode and cannot damp it at any gain. Retires the entire damper-tuning direction (V44/V47). The hand cures it because a grip is collocated at the antinode."
metadata:
  type: reference
---

**★ The keystone that explains why every damper build (V44, V47) failed on-car — and closes that
direction for good.**

The ~21.4 Hz steering vibration is a **two-inertia torsional mode**: assist motor/rack inertia
oscillating against steering-wheel/column inertia, with the **torsion bar (= the torque sensor) as the
intervening compliance.** (Literature corroboration: an EPS state-space model with a complex pole at
~131 rad/s = 20.9 Hz, "ball-screw/motor-rack inertia vibrating due to the torsional stiffness of the
steering wheel and column.") The **wheel/column end is the large-motion antinode; the motor/rack is on
the other side of the torsion bar.**

**Collocated vs non-collocated (Preumont):**
- Gripping the wheel adds mass + damping **at the antinode, on the column side of the torsion bar** —
  **collocated** with the mode → injects real modal damping for ANY gain → reliably kills it. And the
  vibration is worst hands-off because that damping is then absent. (⚠ Operator: only an ACTIVE grip
  quiets it, not a light rest — and openpilot keeps commanding torque through the turn, so the cure is
  the grip's collocated damping, not any drop in excitation.)
- The firmware base-assist damper `FUN_00034350` (Factor E) senses **motor-resolver rate** `gp-0x6ac0`
  — the **far side** of the torsion bar → **non-collocated.** At 21 Hz the torsion-bar compliance
  decouples the wheel inertia from the motor, so the motor barely observes the wheel-side oscillation and
  its correction is isolated from the antinode. Non-collocated velocity feedback can damp some modes and
  **destabilize** others (pole-zero flip). **You cannot reliably damp a wheel-side mode from a rack-side
  velocity sensor at any gain.**

**Consequences (load-bearing):**
1. **STOP tuning the motor-rate damper for the vibration.** V44 (Factor C) and V47 (Factor C + Factor E,
   aggressive) nulls are this theorem confirmed on-car — not bad luck. Do not spend another flash there.
2. Corroboration: the voter `gp-0x6a5e` that Factor C keys on is too slew-limited to even track 21 Hz
   (max trackable ≈ 4.6–45 counts vs the 2240 gate) — so that factor sees DC hand torque, not the ripple.
3. The loop-gain model quantifies it: **bare-plant Q≈1.7, but the 4× gain drives the derivative
   feedbacks to ~0° ANTI-DAMPING → closed-loop Q=13.6, |L(21Hz)|≈0.875, 1.16 dB margin** (onset ~3×,
   hard edge 4.57×). See `analysis-2020accord/eps_loop_gain_model.py`.
4. The theory-correct fixes that keep 4×: **reduce the loop gain at 21 Hz on the collocated
   positive-feedback carriers** (cal-only lane attenuation — tried in V48A, insufficient → distributed),
   or a **NOTCH at 21.4 Hz on the torsion-bar signal** (V48B; the OEM-standard answer; split-independent),
   or a **collocated** damper (bandpassed dτ/dt of the torsion bar). NOT the motor-rate damper.

Master reference: `docs/VIBRATION-DOSSIER.md`. Related: [[reference-accord-damper-two-deadzones-factorC-factorE]]
(now superseded as a *fix* direction — the deadzones are real but the damper is non-collocated),
[[reference-accord-dualpinion-arch-one-torsion-sensor]], [[project-v48-loopgain-v48a-failed-notch-next]].
