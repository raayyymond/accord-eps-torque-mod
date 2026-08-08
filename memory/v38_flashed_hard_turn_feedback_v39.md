---
name: V38 flashed clean; ratchet and vibration led to revised V39
description: V38 is fault-free but has a several-Hz hard-turn ratchet and tens-of-Hz high-LKAS vibration; revised V39 suppresses direct r24 for both signs while leaving r26 and the governor intact.
type: project
---

V38 was flashed by 2026-07-18 and works without dashboard/DTC errors. The operator subsequently separated two behaviors: (1) a several-Hz ratcheting/intermittent stop on hard turns, often after a stop sign or light, and (2) a frequent, sometimes audible tens-of-Hz steering-wheel vibration under high LKAS torque while the wheel moves, at low and high road speed. Strong driver-side torque can move the wheel quickly through the same downstream motor loop without either symptom, contradicting an intrinsic motor-torque-while-moving limit.

Revised V39 is a narrow discriminating build for the high-frequency symptom. At or above the exact V9 full-scale equivalent (`|internal LKAS lane| >= 417`) and low voted driver torque it suppresses direct Sensor-B torque-rate lane `r24` for both signs. The 417 threshold is the lower exact V9 Q15 magnitude: V9 produces +417/-418 at full scale. It retains adaptive derivative lane `r26`, every V38 calibration, and the complete motor-rate governor/shaper/protection path. It does not claim the slower ratchet is solved.

**Why:** The direct four-producer-sample derivative lane is cadence-compatible with a tens-of-Hz loop and can be comparable to the LKAS contribution. Keeping the governor unchanged avoids weakening motor protection and preserves a controlled experiment; the high-driver observation already refutes a universal motor capability limit.

**How to apply:** Treat V38 as on-car validated for fault freedom, not unflashed. Score V39's vibration and ratchet separately. Vibration improvement with a persistent ratchet implicates `r24` only in the high-frequency symptom; persistent vibration points first to `r26` or another outer assist lane, not directly to the governor. Use and continuously update `analysis-2020accord/eps_lkas_chain_model.py` as the live golden reference.
