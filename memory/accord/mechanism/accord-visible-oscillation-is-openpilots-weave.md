---
name: accord-visible-oscillation-is-openpilots-weave
description: The operator's visible steering oscillation is a 0.44-1.3 Hz path weave that openpilot's command LEADS by +47 deg — it is a lateral-loop limit cycle, not the EPS, and it is a SEPARATE defect from the grinding.
metadata:
  node_type: memory
  type: reference
---

# THE VISIBLE OSCILLATION IS OPENPILOT'S WEAVE — NOT THE EPS, AND NOT THE GRINDING

★★★★★ **EVIDENCE for every numbered claim; BELIEF only for the final attribution.** Route `1e` (V107),
998.9 s engaged / 338.6 s manual, 10 engaged episodes, 2026-08-27.

## 1. IT IS REAL, AND IT IS BIG — the operator was right and the kit had been looking in the wrong band
**46 qualifying events, covering 172.7 s = 17.3 % of engaged time.** Largest **24.02° p2p = 77.6 mm at
the rim**; median event 4.2–5.7° = 14–18 mm. **Frequencies 0.44–2.93 Hz.**
🛑 **His "under or around 10 Hz" is really 0.4–1.6 Hz.** Ceiling by band, max p2p over all engaged
windows: 0.4–0.6 Hz **24.02°** · 0.6–1.0 **15.26°** · 1.0–1.6 **9.54°** · 1.6–2.5 6.06° · 2.5–4.0 4.03°
· **4.0–6.3 1.33° (4.3 mm)** · **6.3–10 1.12° (3.6 mm)**.
⇒ **Above 4 Hz the steering angle NEVER reaches a centimetre on any engaged window.** Every earlier
search that scanned 4–10 Hz was structurally incapable of finding this.

## 2. IT IS A PATH MOTION — the car weaves WITH the wheel, every time
Steer→yaw gain calibrated from this route per speed bin (⚠ `carState.yawRate` is identically ZERO on
this car — use `livePose.angularVelocityDevice.z`). Measured yaw p2p ÷ kinematic prediction:
**all 46 events p50 = 1.17, range 0.73–1.61.** Near-straight subset identical (p50 1.16).
⇒ **There is no event in 998.9 s where the wheel moves and the car does not follow.** That **excludes a
column/rack-side torsional oscillation**, which is what an EPS-originated limit cycle would look like.

## 3. ⭐ OPENPILOT'S COMMAND LEADS IT. THE DRIVER'S HANDS LAG IT.
Phase of angle relative to command, measured at each event's own frequency, episode-bootstrapped over 8
episodes. ⚠ Not a raw cross-correlation — at 0.5 Hz a ±1 s lag search is a 180° ambiguity.
```
  ALL 46 events     circular mean +46.8 deg  CI [+29.4, +71.3]  R = 0.581  angle LAGS in 72 %
  NEAR-STRAIGHT     circular mean +63.3 deg                     R = 0.740  angle LAGS in 85 %
  0.40-0.63 Hz  +47.2 deg (median lag +0.273 s)   1.0-1.6 Hz  +47.6 deg (median lag +0.088 s)
  0.63-1.00 Hz  +54.2 deg (+0.222 s)              1.6-4.0 Hz  +10.6 deg (-0.010 s)
```
⭐ **The 1.0–1.6 Hz lag of +0.088 s sits on top of `steerActuatorDelay` = 0.100 s.**
⭐ **The command-leads signature is STRONGER near-straight than cornering** (R 0.740 vs 0.538, 85 % vs
68 %) — **the opposite of what a road-driven artefact would do.**
⊕ **The driver is excluded as the third candidate**: phase of angle vs DRIVER torque is
**−63.2° [−88.1, −24.8]** — the angle **LEADS** driver torque. **The hands are reacting to the wheel.**
⊕ Coherence command↔angle 0.4–3 Hz is **0.46–0.65 against a shuffled floor of 0.24–0.33** (~2×).
⚠ Manual coherence is **NaN, not a null** — `e4tq` is identically zero with LKAS off. Carries no
information; do not quote it.

## 4. ENGAGED IS *QUIETER* THAN THE DRIVER IN THIS BAND
Speed-stratified angle PSD, ratio formed inside each 6 km/h cell then pooled: **engaged/manual =
0.022–0.21 across 0.4–3.5 Hz** — engaged is **5–45× quieter than the driver at the same speed.** And
speed-matched event rates: engaged fires **LESS often than manual in every bin with exposure on both
sides** (0.09×–0.86×).
⇒ **This is not "the firmware is shaking the wheel". It is a controller weaving less than a human, but
periodically — and periodicity is what is visible, not amplitude.**

## 5. 🛑 IT IS **NOT** THE GRINDING. TWO INDEPENDENT DEFECTS.
Inside each event vs a speed-matched engaged baseline (same ±3 km/h cell, event frames removed):
```
  rail duty P(|gp-0x6c2c| >= thr(v))   inside 20.34 %   baseline 20.12 %   ratio 1.01 [0.88, 1.22]
  audio 100 Hz - 2 kHz (within-drive)  mean +0.50 dB    median +0.11 dB    CI [-1.18, +2.54] dB
     control: 399 random matched-speed engaged windows, mean -0.46 dB, 95 % spread [-6.2, +7.9]
```
⇒ **V109 and any successor must target the two separately.** They do not co-occur.

## 6. THE ATTRIBUTION
**[BELIEF, strongly supported, not proven]** A **weave / limit cycle in openpilot's own lateral control
loop.** Three independent lines point one way: the command leads, the hands lag, and the car follows the
wheel kinematically every time. 🛑 **In a closed loop command and angle are mutually causal and phase
alone cannot prove direction** — what the measurement *does* do is make the EPS-originated signature
("angle leads command") a **28 % minority** with a pooled CI excluding zero on the wrong side.
⭐ **It explains why sixty firmware builds never touched it: there was never a firmware lever on it.**
🛑 `feedback-no-openpilot-side-modifications` is a standing instruction — **the operator must be told
this is his call, not ours.**

## 7. WHAT COULD STILL CHANGE IT
1. 🛑 **Manual exposure above 24 km/h on route `1e` is 35.8 s total.** The speed-matched rate ratios
   above 24 km/h rest on **0–2 manual events**, and the stratified PSD only has cells at 6–36 km/h.
   **The 40+ km/h comparison is NOT MEASURED**, and 5 of the 13 near-straight events are at 39–76 km/h.
   ⇒ **Closes with a drive carrying deliberate matched manual segments at 50–80 km/h on the same road.**
2. The steer→yaw gain is empirical from this route, not a vehicle model — used only as an
   order-of-magnitude follow/no-follow test, and every event clears it by a wide margin, so a 30 % gain
   error would flip nothing.
3. Column ROTATION only. He said *"turning — the spoke swings"*, so it is the right channel.

## 8. ⭐ THE METHOD LESSON — a wideband detector would have found NOTHING
A single 0.4–3 Hz band-pass is the **wrong instrument**: at these amplitudes a 0.45 Hz cornering input
**destroys the zero-crossings** of a small 1.2 Hz limit cycle riding on it, so a wideband detector is
**structurally blind to exactly the thing being looked for.** Five sub-bands
(0.40–0.63 / 0.63–1.0 / 1.0–1.6 / 1.6–2.5 / 2.5–4.0 Hz) is what found it.
⊕ Controls that passed first: an injected-sinusoid amplitude ladder (fires as designed, quiet below the
gate) and a **ringing control** — impulse, step and ramp through every band filter, **zero spurious
chains in all 15 combinations**, because a narrow band-pass rings and ringing looks periodic.

Related: [[accord-gp6b26-is-a-61hz-bandpass-and-v107-railed-it]] ·
[[accord-lateral-engagement-signals]] · [[feedback-no-openpilot-side-modifications]]
