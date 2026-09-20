# The low-speed hold feedforward is missing an ADDITIVE intercept, not stiffness — and the fork's own supplier points the wrong way

**Measured 2026-09-19**, torque mode (V293), 2–8 m/s hands-off, 145 dwell/breakaway episodes, 5 routes.
Hand-checked by the orchestrator: `rlog-tools/studies/v282-reference/lowspeed/a_stickslip/orch_crux_check.py`
and `orch_crux_check2.py`, each gated on reproducing `ss_centring_fit`'s five coefficients to <5e-7 first.
Full write-up in that study's `REPORT.md`.

## The measurement, regressor-free

`S = (median cmd·sign(angle)|away + median cmd·sign(angle)|toward)/2` at breakaway. Outward breakaways sit on the
band's upper edge `S+F`, inward on the lower `S−F`, so the average IS the band centre — **no fit, no `k`, no `c`,
no episode selection.** Map recomputed per route honouring its own flown `AccordHoldLevel`.

| \|angle\| deg | S | levelled MAP | SHORTFALL | required MULTIPLIER |
|---|---|---|---|---|
| 0.6–2.5 | +0.0259 | +0.0028 | **+0.0231** | **9.2x** |
| 2.5–10 | +0.0555 | +0.0113 | **+0.0442** | **4.9x** |
| >10 | +0.1051 | +0.0716 | +0.0335 | **1.5x** |

⇒ **The deficit is ADDITIVE and saturating, with a knee below ~1 deg** (requirement at <0.4 deg is only +0.0006).
The hold feedforward supplies just 20–35% of the command that actually holds the wheel at 2–8 m/s.

## 🛑 Every MULTIPLICATIVE lever is DOMINATED, not merely imprecise

The required multiplier spans 9.2x → 1.5x. Sized for 1 deg it over-holds several-fold at 8 deg; sized for 8 deg it
delivers a fraction of what 1 deg needs. **`AccordHoldLevel`, the `HONDA_ACCORD_HOLD_K_V` schedule and
`AccordEpsSpringScale` are disqualified on SHAPE, at any dose.** No existing toggle has the right parity ⇒ any
remedy is a small fork code change, not a toggle config.

## ⭐ Why it is missing: the fork believes `AccordFrictionHyst` supplies it. It does not.

`latcontrol_vehicle_tunes.py:227` — the map "was fitted with a static-friction intercept of 0.020 torque, which is
NOT in the table: the hysteresis feedforward (AccordFrictionHyst) supplies it in the direction of the last desired
motion." `HONDA_ACCORD_HOLD_STATIC_FRICTION = 0.020` at `:273` is **defined and read by no code**.

Measured z at breakaway, projected into the outward frame: **pooled median −0.0038, CI [−0.0060, −0.0030]** against
a deficit of **+0.0231** — wrong sign, all 5 routes (6c −0.0066, 6d +0.0012, 6e −0.0030, 75 −0.0038, 76 −0.0032),
while `|z|` median is 0.0095, i.e. **the term IS running.** It is keyed on *desired-angle motion*, and a dwell is
*defined* by the demand moving, so it points wherever the demand points — not outward.

## Nothing winds during the stick

Median change dwell-start → breakaway, outward frame: **`dob` exactly +0.0000** in every populated bin, `I`
+0.0005…+0.0012, against a centre of 0.02–0.09; the command is already at full level at dwell start and then
*decays* (−0.0144 at 0.6–2.5 deg). ⇒ The deficit is a **STANDING condition the stick does not create.** The
integrators only CARRY it, interchangeably — route 75 flew the observer OFF and its PID's I carries the same amount.

## 🛑 The 0.033 "Coulomb half-width" is NOT Coulomb

F at matched angle 0.6–2.5 deg: **+0.0030 at dwell start** → +0.0048 → +0.0073 → **+0.0353 at breakaway−3** while
S holds 0.0234→0.0259. F at detection is an upper bound containing command overshoot past the true edge plus the
0.3 deg detector lag. **Do not re-size `AccordFrictionHyst` against 0.033** — the "0.015 = 45% of measured"
framing is void. True Coulomb is unresolved between the fork's separately identified 0.010–0.012 and ~0.030.

## 🛑 Two traps recorded because they each cost a wrong answer here

1. **Subtracting a LINEAR `k*|angle|` from a saturating map manufactures an angle-dependent residual.** An earlier
   orchestrator pass read the centre as "angle-proportional, spans 454x" and concluded the 0.020 constant does not
   exist. Both halves were wrong: the 454x was the first quintile straddling zero, and `k=0.00556` removes 0.056
   torque at 10 deg — steeper than the map. **Bin against the fork's own nonlinear map, never against a linear fit.**
2. **The `AccordHoldLevel` on/off contrast is an IDENTITY, not an experiment.** S is a property of the car, so
   turning the level off moves `S − map` by exactly +0.15·map under *every* cause. Measured move +0.0004 against a
   within-arm route scatter of 0.021 (19x). No number of repeats fixes it.

## The design question that comes BEFORE any drive

`get_honda_accord_hold_torque` is **also the disturbance observer's internal model**, and the observer is called
with the **measured** angle. Put an additive near-relay term inside that function and it sits inside a loop whose
DC gain is ~1 above 6 m/s — the class that produced route 71's 2.34 Hz limit cycle. Leave it out and the observer
reads the raise as a disturbance and cancels it inside its 0.6 Hz corner (the fork's own comment at `:263`).
A design must state which, and show the relay margin at zero angle.

Related: [[accord-v293-flew-route70-plant-is-a-spring-ratchet-measured]] ·
[[accord-torque-mode-loop-delay-is-55-75ms-and-xcorr-cannot-measure-it]] ·
[[accord-lowspeed-actuator-rails-on-large-angle-transients]] ·
[[feedback-fork-side-experiments-are-toggle-configs-not-code]]
