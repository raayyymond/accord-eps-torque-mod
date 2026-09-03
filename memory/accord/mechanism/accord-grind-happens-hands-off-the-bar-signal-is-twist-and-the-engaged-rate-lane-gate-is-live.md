---
name: accord-grind-happens-hands-off-the-bar-signal-is-twist-and-the-engaged-rate-lane-gate-is-live
description: Operator 2026-09-03, verbatim -- "my hands are not on the steering wheel for grind to happen." So the 0x18F driver-torque channel during grind (a 20 Hz line, 140-280 raw, coherent with wheel rate and the delivered-torque tap, engaged-only, 3-6 mph) is PURE column twist, a plant state, and the loop has no driver in it. Image-verified the same day: since V104 the car carries byte 0x3AA96 = fb (stock c5), which repoints the base-assist rate-lane gate from the dead cell gp-0x683c to gp-0x6806 STEER_CONTROL_ACTIVE, so when LKAS is engaged r24 takes FLAT gain 0xC6446 = 5244 (stock 512, x10.24) on the 4-tap time-derivative of the torsion-bar torque (gp-0x4f62), unfiltered into the 1 kHz motor sum; r26 gated the same way (0xC6444 = 512). Absent on stock/V38/V62/V101-V103; present on V67/V68/V104/V112/V122/V268/V276/V278/V280. The record's "Lever B is unreachable" (gp-0x683c zero writers) and this are both true: the dead cell is bypassed, not armed. #1 candidate for the engaged-only grind (fwloops20 census) and a candidate for the 7 Hz strong-turn ripple (bar rings 1000-2200 raw there). Clean discriminator in the lineage: V103 (gate off, route 0x9e) vs V104 (gate on, route a4).
metadata:
  type: reference
---

# Grind is hands-OFF; the bar signal is twist; the engaged rate-lane gate is live on the car -- 2026-09-03

| fact | status | method |
|---|---|---|
| hands are off the wheel when the grind happens | EVIDENCE (operator) | his words, 2026-09-03 |
| 0x3AA96 = fb on V112/V268/V280, c5 on stock/V38/V62/V101-V103 | EVIDENCE | raw byte read of every image |
| fb repoints `ld.bu` from gp-0x683c to gp-0x6806 (hw1 unchanged; V850 bit-5 displacement rule) | EVIDENCE | fwloops20, `docs/traces/TRACE-2026-09-03-engaged-only-loops-at-20hz.md` |
| gp-0x683c still has zero writers on V280; gp-0x6806 has 16 (same set as stock) | EVIDENCE | two byte-scan censuses |
| 0xC6446 = 5244 (r24 flat gain, x5.12 Q10) and 0xC6444 = 512 (r26) on the car | EVIDENCE | byte read |
| r24's input gp-0x4f62 = 4-tap backward difference of gp-0x4f60 (bar torque), -0.09 dB / +75.6 deg at 20 Hz vs an ideal derivative | EVIDENCE (prior tracer memory) | FUN_0007e74a |
| r24 is the 20 Hz grind driver / the 7 Hz ripple carrier | BELIEF | pending creep20 / twistloop |

Open: the 0x18F torque <-> gp-0x4f60 scale is not proven identical; the torsion-bar stiffness is not on record, so r24's gain per deg/s of wheel rate cannot be stated yet.
Levers: (i) 0x3AA96 fb -> c5 (1 code byte; the flown state of V101-V103 and every pre-V67 build; both lanes fall back to Honda's surfaces when engaged); (ii) 0xC6446 5244 -> 512 (cal-only).

Related: [[accord-lever-b-is-unreachable]], [[accord-rate-lane-gain-surface-found]], [[accord-lanechange-ring-is-the-outer-loop-the-map-never-touches-the-eps-rate-feedback-gain]], [[accord-v62-rate-lane-was-silently-lost]].
