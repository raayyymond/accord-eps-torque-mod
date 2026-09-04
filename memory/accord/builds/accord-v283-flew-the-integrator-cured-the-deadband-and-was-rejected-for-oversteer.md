---
name: accord-v283-flew-the-integrator-cured-the-deadband-and-was-rejected-for-oversteer
description: 2026-09-03/04, routes ..._00000036 / _00000037 / _00000038 (r36/r37/r38; 897.3/484.4/848.3 s, 633.6/260.4/707.5 engaged), tune unmoved SR 12.50 / LAF 2.110 / kp 0.600. V283 (= V282 + Ki 50 at 0xC63E6) is the FIRST integrator ever flown on this car. Its prereg PASS sentence FIRED - stalls 7 -> 1 pooled, (b) 87 %, (c) 0.048, (e) F7 0.00 unchanged: Ki 50 CURED V281 rev 3's P-only deadband. It was still REJECTED, on the drive (tight-curve achieved/asked 0.996 -> 1.278; matched-frame delta +0.334 m/s^2 on an SR-free instrument; inner DC gain 0.36 -> 0.76) and on principle - the operator: "an integrator on steering angle rate is just steering angle, which would NOT be used in a PID loop on angular acceleration". NEW RESIDUAL: the EPS integrator DOES NOT CLEAR AT DISENGAGE - 139-383 counts still delivered 0.5-1.0 s after STEER_REQUEST drops, where both Ki-0 builds are at zero within 0.5 s. Ki does NOT touch the 20 Hz grind line (1.10, p = 0.38). The operator's frontier build reverts to V282.
metadata:
  type: project
---

# V283 flew: the integrator cured the deadband, and was rejected anyway — 2026-09-03/04

**Build:** V283 = V282 + `0xC63E6` 0 → 50 (5 bytes incl. the page CRC). Image `fd0c321a…1ef3d`.
**Routes:** `…_00000036` (r36, 897.3 s / 633.6 s engaged) · `…_00000037` (r37, 484.4 / 260.4) ·
`…_00000038` (r38, 848.3 / 707.5). All three tap-attributed to V283 (Ki fitted **51.9 / 52.0 / 52.1**
against a 1.2–1.9 control floor; Kp flat 248; V282's bit 6 alive). Tune unmoved: SR 12.50 / LAF 2.110 /
kp 0.600.

## It worked, on its own prereg

| prereg endpoint | result |
|---|---|
| stalled runs ≥ 1 s | **7 → 1** pooled |
| (b) idx 40–80 rate vs reference | **87 %** (was 45 %) |
| (c) dead fraction | **0.048** (was 0.34) |
| (e) F7 episodes | **0.00**, unchanged |

⇒ **Ki 50 cured the P-only deadband** that V281 rev 3 created
([[accord-v281r3-flew-the-7hz-cycle-is-gone-the-p-only-deadband-arrived-understeer-is-mostly-sr-12-5]]).
It is the only intervention in the arc that has moved the stall class.

## It was rejected anyway — two reasons, and the second is the durable one

**On the drive.** Tight-curve achieved÷asked **0.996 → 1.278**; matched-frame Δ **+0.334 m/s²** on an
SR-free instrument (livePose yaw·v with roll removed); inner DC gain **0.36 → 0.76**. The mechanism is
the integrator's **DC face** — exactly the term the cure works through.

**On principle** (operator, 2026-09-04, and this is the part that redirects the programme):
> *"I don't like the idea of the integrator anyways, it goes against what openpilot is modelling its
> output as, a torque. An integrator on steering angle rate is just steering angle, which would NOT be
> used in a PID loop on angular acceleration (proportional to torque)."*

He is right on the arithmetic —
[[accord-the-rate-pid-in-the-acceleration-frame-is-a-PI-our-P-is-its-integral-and-our-D-is-its-proportional]].
In the acceleration frame our I term is a **double integral**. His frontier build reverts to **V282**.

## 🛑 NEW RESIDUAL — the integrator does not clear at disengage

139–383 counts are **still being delivered 0.5–1.0 s after `STEER_REQUEST` drops**. Both Ki-0 builds are
at zero within 0.5 s. Adversarial pass B had flagged the class before the flight (*"reset lags disengage
0.1–1 s"*) and the drive confirmed it — the reset path at `0x2A164` exists but does not win the race.
**Any future integrator on this loop must fix that first.**

## What Ki did NOT do

**Ki does not touch the 20 Hz grind line** (ratio 1.10, p = 0.38) — consistent with its 0.25 Hz corner.
Grinding held V281 rev 3's gain (~3× rarer, ~2.2× smaller than V280 rev 2), with no r35-class incident.

## Reading note for whoever compares builds against V283

🛑 **SteerRatio 12.5 is an UNDERSTEER bias, not an oversteer brake** — SR enters only
`measured_curvature`, so a lower SR over-reads curvature and the controller under-turns. Do not raise SR
while assessing an integrator change; it confounds. And openpilot was **barely commanding in steady
curves** on these routes (f +0.800 cancelled by p −0.300, i −0.392; net +0.108; median signed output
+0.009), with over-delivery moving *inversely* with command — so "oversteer" here is an EPS-side DC
gain, not an outer-loop command.
