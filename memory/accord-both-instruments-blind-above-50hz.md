---
name: accord-both-instruments-blind-above-50hz
description: CAN and the comma IMU both sample near 100 Hz, so nothing above ~50 Hz is observable — and the IMU gives NO headroom over CAN
metadata:
  type: reference
---

🛑🛑 **EVERY INSTRUMENT THIS KIT HAS IS BLIND ABOVE ~50 Hz.** Measured from hardware timestamps on
route 47 and route 3a:

| instrument | measured rate | **Nyquist** |
|---|---|---|
| CAN `0x14A` / `0x18F` grid | ~100.5 Hz | **50.2 Hz** |
| comma IMU accelerometer (LSM6DS3TR-C, hardware clock) | **99.9–100.5 Hz** | **49.97–50.26 Hz** |

⇒ **The IMU gives NO headroom whatsoever over CAN.** It was introduced as the independent sensor for
grind #2 and it is genuinely independent of the EPS signal path — but it is **not** an independent
*bandwidth*.

## Two consequences that must be carried into every future analysis

1. **A null above ~50 Hz is not a null — it is silence.** If a felt vibration is genuinely above 50 Hz,
   no measurement in this kit can see it, and any "we measured nothing" statement is only about the
   observable band. State that limit explicitly rather than letting the null read as an absence.
   This is live right now: the operator reports a highway resonance that shows **no** signature in
   either channel (see [[accord-v67-flew-both-grinds-fixed]]).

2. **IMU/CAN frequency agreement carries ZERO information about the alias.** Grind #2's "44.9 Hz" is
   aliased — 44.9 and ~55.6 Hz are the same observation on a 100.5 Hz grid — and because the two grids
   are only **0.5 Hz apart**, agreement between them cannot break the degeneracy. Never quote it as if
   it could. A dedicated fold test and a Lomb–Scargle test on true arrival timestamps both came back
   underpowered.

## What would actually break the barrier
The firmware's own control task runs at **1 kHz**. A probe that samples inside that task and reports a
**sticky / accumulating** flag on the 100 Hz CAN channel — e.g. a bit latched when `|gp-0x4f62|` crosses
a threshold and cleared when the payload is written — would report HF *energy* without aliasing.
🛑 It needs a RAM cell, so **GATE 1 stops being vacuous**, and that is the class that bricked V24/V27/
V48B. `gp-0x1500` passed both static clearance methods and still failed on-car. Prove ownership two ways
or do not build it.

Raising the comma's IMU sample rate would also work but is **out of bounds** — no openpilot-side
modifications ([[feedback-no-openpilot-side-modifications]]).
